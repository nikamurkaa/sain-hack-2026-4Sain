"""Регрессии контекста, частичных ошибок и финального сеанса."""
import asyncio
import json
from copy import deepcopy
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from backend.core import ServiceError
from backend.runner import open_solution
from tests.helpers import AT, FakeModel
from tests.test_integration import Simulator, insert_session
from main import app


class ConversationModel(FakeModel):
    def __init__(self):
        self.turns = []

    async def json(self, instruction, payload, output_tokens=3500):
        if 'utterances' not in payload:
            return {'facts': []}
        self.turns.append(deepcopy(payload))
        if payload['utterances'] == ['Ещё немного']:
            assert payload['history'][-1]['utterances'] == ['Прохладнее']
            return {'intent': 'cooler'}
        return {'intent': 'cooler'}


def test_requests_keep_history_and_current_record_state():
    async def check():
        sim = Simulator()
        first = sim.data['requests'][0]
        first['utterances'][0]['text'] = 'Прохладнее'
        second = deepcopy(first)
        second.update(record_id='second', at='2026-11-12T20:01:00+03:00')
        second['utterances'][0].update(text='Ещё немного', at=second['at'])
        # Вход намеренно переставлен. Обработка хронологическая, ответ в исходном порядке.
        sim.data['requests'] = [second, first]
        model = ConversationModel()
        async with httpx.AsyncClient(transport=httpx.MockTransport(sim), trust_env=False) as http:
            solution = await open_solution('eval', 'case2-dev-v1', http, model)
            answer = await solution.run()
        assert [turn['utterances'] for turn in model.turns] == [['Прохладнее'], ['Ещё немного']]
        assert model.turns[0]['history'] == []
        assert [item['record_id'] for item in answer['requests']] == ['second', 'request_test']
        for saved in sim.sessions.values():
            if saved['session']['kind'] == 'request':
                command = saved['entries'][0]['steps'][0]
                assert command['values']['temperature_c'] == saved['session']['initial_state']['climate']['temperature_c'] - 1
    asyncio.run(check())


def test_client_successful_turn_is_available_to_next_message():
    with TestClient(app) as client:
        session = insert_session('guest')
        session.solution.model = ConversationModel()
        headers = {'Authorization': 'Bearer guest', 'Idempotency-Key': 'first-message'}
        assert client.post('/api/v1/messages', headers=headers, json={'text':'Прохладнее', 'at':AT}).status_code == 200
        headers['Idempotency-Key'] = 'second-message'
        result = client.post('/api/v1/messages', headers=headers, json={'text':'Ещё немного', 'at':AT})
        assert result.status_code == 200, result.text
        assert len(session.history) == 2
        assert session.room.executions == 2


def test_failed_request_does_not_discard_other_answers():
    async def check():
        sim = Simulator()
        second = deepcopy(sim.data['requests'][0])
        second['record_id'] = 'second'
        sim.data['requests'].append(second)
        async with httpx.AsyncClient(transport=httpx.MockTransport(sim), trust_env=False) as http:
            solution = await open_solution('eval', 'case2-dev-v1', http, FakeModel())
            original = solution.message
            async def sometimes_fails(room, *args, **kwargs):
                if room.session['session_id'] == 'session_request_test':
                    raise ServiceError('ACTION_UNCONFIRMED', 'Не подтверждено')
                return await original(room, *args, **kwargs)
            solution.message = sometimes_fails
            answer = await solution.run()
        assert [item['replies'][0]['response_class'] for item in answer['requests']] == ['refused','done']
        assert len(answer['stays']) == 1
    asyncio.run(check())


def test_final_session_reuses_prepared_user_without_reloading(monkeypatch):
    monkeypatch.setenv('HACK_TEAM_TOKEN', 'team')
    sim = Simulator()
    sim.data['meta']['phase'] = 'final'
    sim.data['requests'] = []
    with TestClient(app) as client:
        async def fake_open(token, code, http, model, team_token):
            transport = httpx.AsyncClient(transport=httpx.MockTransport(sim), trust_env=False)
            return await open_solution(token, code, transport, FakeModel())
        with patch('main.open_solution', side_effect=fake_open):
            result = client.post('/run', headers={'Authorization':'Bearer final-eval'},
                                 json={'case':2,'dataset_code':'case2-final-test'})
            assert result.status_code == 200, result.text
        reads = sim.reads
        headers = {'Authorization':'Bearer team'}
        first = client.post('/api/v1/sessions', headers=headers, json={'source':'final'})
        assert first.status_code == 201, first.text
        token = first.json()['session_token']
        message_headers = {'Authorization':'Bearer '+token,'Idempotency-Key':'final-message'}
        assert client.post('/api/v1/messages', headers=message_headers,
                           json={'text':'Теплее','at':AT}).status_code == 200
        second = client.post('/api/v1/sessions', headers=headers, json={'source':'final'})
        assert second.status_code == 201
        assert sim.reads == reads
        assert len(sim.sessions) == 1
        assert len(app.state.final_session.history) == 1
        assert set(sim.auth) == {'Bearer final-eval'}
        assert client.post('/api/v1/sessions', headers={'Authorization':'Bearer stranger'},
                           json={'source':'final'}).status_code == 403


def test_missing_request_session_keeps_other_records():
    async def check():
        sim = Simulator()
        second = deepcopy(sim.data['requests'][0])
        second['record_id'] = 'second'
        sim.data['requests'].append(second)
        def unavailable(request):
            if request.url.path == '/room/session' and json.loads(request.content)['record_id'] == 'request_test':
                return httpx.Response(403, json={'code':'ACCESS_DENIED'})
            return sim(request)
        async with httpx.AsyncClient(transport=httpx.MockTransport(unavailable), trust_env=False) as http:
            solution = await open_solution('eval', 'case2-dev-v1', http, FakeModel())
            answer = await solution.run()
        assert [item['record_id'] for item in answer['requests']] == ['second']
        assert len(answer['stays']) == 1
    asyncio.run(check())


def test_profile_dislike_has_a_verifiable_source():
    from backend.preferences import PreferenceResolver
    from tests.helpers import dataset
    class ProfileModel(FakeModel):
        async def json(self, instruction, payload, output_tokens=3500):
            source = next(item for item in payload['history'] if item['id'] == 'profile:dislikes')
            return {'facts':[{'key':'alarm_mode', 'value':'light',
                              'source_id':source['id'], 'quote':source['text']}]}
    async def check():
        data = dataset()
        data['users'][0]['sleep_preferences'] = {
            'temperature':None, 'favorite_track_ids':None, 'light_sensitive':None,
            'dislikes':['резкие звуки будильника']}
        resolver = PreferenceResolver(data, ProfileModel())
        prefs = await resolver.resolve('guest_test', AT, '2026-11-11')
        assert prefs['alarm_mode'] == 'light'
        assert prefs['sources']['alarm_mode']['source'] == 'profile:dislikes'
    asyncio.run(check())



def test_hotel_and_home_sources_remain_distinct():
    from backend.preferences import PreferenceResolver
    from tests.helpers import dataset

    class SourceModel(FakeModel):
        async def json(self, instruction, payload, output_tokens=3500):
            hotel, = payload["hotel_notes"]
            home, = payload["history"]
            assert hotel["source"] == "hotel" and home["source"] == "app"
            return {"facts": [
                {"key": "temperature", "value": "warm", "source_id": hotel["id"], "quote": hotel["text"]},
                {"key": "home.climate.temperature_c", "value": 19, "source_id": home["id"], "quote": home["text"]},
            ]}

    data = dataset()
    for source, text in [("hotel", "Здесь всегда прошу 22 градуса."), ("app", "Дома ставлю 19 градусов.")]:
        data["events"].append({"event_id": source, "source": source, "user_id": "guest_test",
                               "started_at": AT, "payload": {"text": text}})
    prefs = asyncio.run(PreferenceResolver(data, SourceModel()).resolve("guest_test", AT, "2026-11-11"))
    assert prefs["temperature"] == "warm"
    assert prefs["home"]["climate"]["temperature_c"] == 19
