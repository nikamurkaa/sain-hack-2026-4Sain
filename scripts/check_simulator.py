"""Проверка подключения к dev-симулятору без обращений к языковой модели.

Запуск из корня: python -m scripts.check_simulator
Нужен HACK_TEAM_TOKEN. Проверка создаёт отдельный dev-прогон и меняет только его комнаты.
"""
import asyncio
import json
import os
from datetime import timedelta
import httpx
from backend.clients import HackClient
from backend.core import iso, moment
from backend.room import Room
from backend.scheduler import bedtime, build_scenario


async def check():
    async with httpx.AsyncClient(follow_redirects=False) as http:
        client = HackClient(os.environ['HACK_TEAM_TOKEN'], http)
        data = await client.dataset('case2-dev-v1')
        run = await client.dev_run()
        stay = data['stays'][0]
        user = next(u for u in data['users'] if u['user_id'] == stay['user_id'])
        # Это техническая проверка транспорта, не оценка персонализации.
        prefs = {'temperature': 'neutral', 'tracks': [], 'volume': 15, 'timer': 30, 'alarm_mode': 'both'}
        steps = build_scenario(user, stay, prefs, data['devices'], data['sleep_rules'])
        room = await Room.create(client, stay['record_id'], 'stay', run['run_id'])
        await room.scenario(steps)
        at = iso(max(moment(stay['check_in_at']), bedtime(user, stay) + timedelta(minutes=5)))
        state = await room.state(at)
        assert state['light']['brightness'] == 0
        assert state['dnd']['enabled'] is True
        assert state['climate']['temperature_c'] == 19.5
        request = data['requests'][0]
        room = await Room.create(client, request['record_id'], 'request', run['run_id'])
        before = await room.state(request['at'])
        new_value = 22 if before['climate']['temperature_c'] != 22 else 21
        after = await room.execute([{'device_id': 'climate', 'values': {'temperature_c': new_value}, 'at': request['at']}], request['at'])
        assert after['climate']['temperature_c'] == new_value
        for device, fields in before.items():
            for field, value in fields.items():
                if (device, field) != ('climate', 'temperature_c'):
                    assert after[device][field] == value
        return {'scenario_saved': True, 'night_state_confirmed': True, 'action_confirmed': True,
                'other_fields_preserved': True, 'api_calls': client.calls, 'llm_calls': 0}


if __name__ == '__main__':
    print(json.dumps(asyncio.run(check()), ensure_ascii=False, indent=2))
