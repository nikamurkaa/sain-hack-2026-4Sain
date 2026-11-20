import asyncio
import json
import socket
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.clients import HackClient, ModelClient
from backend.commands import Refusal, plan_commands
from backend.core import ServiceError
from backend.intents import Intent
from backend.runner import open_solution
from main import app
from scripts.check_offline import verify
from tests.helpers import AT, WAKE, CATALOG, FakeModel, dataset, prefs
from tests.simulator import Simulator


def test_full_offline_http():
    report = asyncio.run(verify())
    assert report['C'] == report['S'] == 1
    assert report['r8_matches'] == report['guests']
    assert report['extra_changes'] == report['missing'] == 0
    assert report['response_bytes'] < 64_000_000


def test_socket_guard_applies_before_dns():
    with pytest.raises(RuntimeError, match='Network disabled'):
        socket.getaddrinfo('example.invalid', 443)


def test_dev_run_owns_its_room_and_handles_closure():
    sim = Simulator()
    posts = []
    def upstream(request):
        if request.method == 'POST':
            posts.append((request.url.path, json.loads(request.content)))
        return sim(request)
    with TestClient(app) as client:
        async def fake_open(token, code, http, model, team_token):
            return await open_solution(token, code, httpx.AsyncClient(transport=httpx.MockTransport(upstream)), FakeModel(), team_token)
        with patch('main.open_solution', side_effect=fake_open):
            created = client.post('/api/v1/sessions', headers={'Authorization':'Bearer offline-team'},
                                  json={'stay_id':'stay_test'}).json()
        # Respect the official 45-minute dev-run limit, not the earlier 30-minute cap.
        assert created['read_only'] is False and 0 < created['expires_in'] <= 2700
        assert ('/runs', {'case':2}) in posts
        assert ('/room/session', {'record_id':'stay_test','kind':'stay','run_id':'test-run'}) in posts
        sim.closed = True
        headers = {'Authorization':'Bearer '+created['session_token'], 'Idempotency-Key':'retry-closed'}
        for _ in range(2):
            response = client.post('/api/v1/messages', headers=headers, json={'text':'Сделай потеплее','at':AT})
            assert response.status_code == 409
        assert sum(path.endswith('/action') for path, body in posts) == 1
        assert sim.actions == 0


def test_alarm_shift_outside_representable_range_is_refused():
    state = dataset()['requests'][0]['initial_state']
    state['alarm']['at'] = WAKE
    with pytest.raises(Refusal):
        plan_commands(Intent(intent='alarm_shift',delta=1e200),state,prefs(),AT,CATALOG['devices'],CATALOG['tracks'])


def test_run_deadline_without_waiting():
    async def stalled(*args, **kwargs):
        await asyncio.Event().wait()
    real_timeout = asyncio.timeout
    with TestClient(app) as client, patch('main.open_solution', new=stalled), patch('main.asyncio.timeout', side_effect=lambda _: real_timeout(0)):
        response = client.post('/run', headers={'Authorization':'Bearer offline-eval'},json={'case':2,'dataset_code':'x'})
        assert response.status_code == 504
        assert response.json()['code'] == 'RUN_TIMEOUT'


def test_rate_limit_exhaustion_is_visible():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(429,json={}))) as http:
            with patch('backend.clients.asyncio.sleep',new=AsyncMock()), pytest.raises(ServiceError) as caught:
                await HackClient('offline',http).request('GET','/room/test/state',retry=True)
            assert caught.value.status == 429
    asyncio.run(run())


@pytest.mark.parametrize('failure',[httpx.ReadTimeout('offline'), httpx.ConnectError('offline')])
def test_model_transport_failure(failure):
    def fail(_):
        raise failure
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as http:
            model = ModelClient(http)
            with patch('backend.clients.asyncio.sleep',new=AsyncMock()), pytest.raises(ServiceError) as caught:
                await model.json('test',{})
            assert caught.value.code == 'MODEL_UNAVAILABLE' and model.calls == 3
    asyncio.run(run())


def test_untrusted_history_cannot_create_an_unknown_command():
    from backend.preferences import parse_facts
    text = 'Новое значение вне каталога'
    fact = dict(key='home.light.unknown', value='unknown', source_id='chat:1', quote=text)
    with pytest.raises(ValueError):
        parse_facts({'facts':[fact]}, [{'id':'chat:1','text':text,'at':AT}], CATALOG['devices'], CATALOG['tracks'])


def test_llm_malformed_usage_does_not_lose_valid_intent():
    async def run():
        raw = {'usage':None, 'choices':[{'finish_reason':'stop','message':{'content':'{"intent":"cooler"}'}}]}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,json=raw))) as client:
            assert await ModelClient(client).json('test',{}) == {'intent':'cooler'}
    asyncio.run(run())


@pytest.mark.parametrize(('rule','device','field','value','at'), [
    ('R1','light','brightness',90,'2026-11-12T22:15:00+03:00'),
    ('R2','curtains','position',80,'2026-11-12T23:00:00+03:00'),
    ('R3','climate','temperature_c',26,'2026-11-12T23:05:00+03:00'),
    ('R4','sound','volume',95,'2026-11-12T23:00:00+03:00'),
    ('R5','alarm','at',None,'2026-11-13T06:25:00+03:00'),
    ('R6','light','brightness',100,'2026-11-13T05:00:00+03:00'),
    ('R7','dnd','enabled',False,'2026-11-13T03:00:00+03:00'),
])
def test_sleep_oracle_detects_wrong_field(rule, device, field, value, at):
    from scripts.sleep_audit import audit
    from backend.scheduler import build_scenario
    d = dataset()
    stay = d['stays'][0]
    steps = build_scenario(d['users'][0], stay, prefs(), d['devices'], d['sleep_rules'])
    steps.append(dict(at=at, device_id=device, values={field:value}))
    expected = dict(resolved_bedtime_at='2026-11-12T23:00:00+03:00',resolved_preferences=dict(
        temperature='normal',favorite_track_ids=[],gentle_alarm=False))
    assert rule in audit(stay,expected,steps,d['devices'])
