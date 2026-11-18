import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.clients import HackClient
from backend.commands import Refusal, plan_commands, success_text
from backend.intents import Intent, parse_intent
from backend.room import Room
from backend.scheduler import build_scenario
from backend.core import ServiceError, default_state, moment
from main import app
from tests.helpers import AT, CATALOG, dataset, prefs
from tests.test_integration import insert_session


def test_common_request_uses_validated_commands_without_model_call():
    async def check():
        class NoModel:
            async def json(self, *args):
                pytest.fail('Для точной короткой просьбы модель не нужна')
        intent = await parse_intent(NoModel(), ['Сделай попрохладнее.'], [], [])
        state = default_state(CATALOG['devices'])
        commands = plan_commands(intent, state, prefs(), AT, CATALOG['devices'], CATALOG['tracks'])
        assert commands[0]['values']['temperature_c'] == state['climate']['temperature_c'] - 1
        state['climate']['temperature_c'] = 16
        with pytest.raises(Refusal):
            plan_commands(intent, state, prefs(), AT, CATALOG['devices'], CATALOG['tracks'])
    asyncio.run(check())


def test_invalid_temperature_reports_actual_catalog_range():
    with pytest.raises(Refusal, match='16.*26'):
        plan_commands(Intent(intent='warmer',value=35), default_state(CATALOG['devices']),
                      prefs(), AT, CATALOG['devices'], CATALOG['tracks'])


def test_empty_message_does_not_execute():
    with TestClient(app) as client:
        session = insert_session('guest')
        response = client.post('/api/v1/messages', headers={
            'Authorization':'Bearer guest','Idempotency-Key':'empty-message'},json={'text':'   ','at':AT})
        assert response.status_code == 422
        assert session.room.executions == 0


@pytest.mark.parametrize('late,timezone',[(True,None),(False,None),(True,'Asia/Vladivostok')])
def test_late_arrival_and_missing_home_zone_produce_valid_steps(late, timezone):
    data = dataset()
    user, stay = data['users'][0], data['stays'][0]
    user['timezone'] = timezone
    if late:
        stay['check_in_at'] = '2026-11-13T00:30:00+03:00'
    steps = build_scenario(user,stay,prefs(),data['devices'],data['sleep_rules'])
    assert steps
    assert all(moment(stay['check_in_at']) <= moment(step['at']) <= moment(stay['target_wake_at']) for step in steps)
    first_night = [step for step in steps if step['at'] == stay['check_in_at']]
    if late:
        assert any(step['device_id'] == 'light' and step['values'].get('brightness') == 0 for step in first_night)


def test_upstream_array_is_rejected_without_content_leak():
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200,json=['private'])),trust_env=False) as http:
            with pytest.raises(ServiceError, match='некорректный'):
                await HackClient('test',http).request('GET','/test')
    asyncio.run(check())


def test_malformed_room_state_is_a_service_error():
    async def check():
        async def request(*args, **kwargs):
            return {'state': {}}
        room = Room(SimpleNamespace(request=request), {'session_id':'test','initial_state':{'climate':{'temperature_c':23}}})
        with pytest.raises(ServiceError):
            await room.state(AT)
    asyncio.run(check())


def test_success_reply_has_units_and_local_alarm_time():
    text = success_text([
        {'device_id':'climate','values':{'temperature_c':21},'at':AT},
        {'device_id':'alarm','values':{'at':'2026-11-13T07:30:00+03:00'},'at':AT}])
    assert '21 °C' in text
    assert '07:30' in text
    assert '2026-' not in text


def test_dev_report_does_not_hide_skipped_records():
    from scripts.check_dev import missing_records
    assert missing_records([{"record_id":"one"},{"record_id":"two"}], [{"record_id":"one"}]) == ["two"]
