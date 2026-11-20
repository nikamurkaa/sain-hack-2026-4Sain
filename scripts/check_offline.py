"""Автономный HTTP-прогон. Запуск: python -m scripts.check_offline."""
import asyncio
import json
import os
import time
from unittest.mock import patch

import httpx
from jsonschema import Draft202012Validator, FormatChecker
from pathlib import Path
from main import app
from scripts.offline_guard import FAKE_ENV, block_network
from scripts.sleep_audit import audit
from tests.offline_cases import ScriptedModel, fixture
from tests.simulator import Simulator


async def verify():
    import resource  # Linux-стенд: ru_maxrss в КиБ.
    started = time.monotonic()
    sim = Simulator()
    sim.data, expected, beds = fixture()
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.MockTransport(sim), trust_env=False
    ) as upstream, httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://app.invalid') as client:
        app.state.http, app.state.model = upstream, ScriptedModel()
        response = await client.post('/run', headers={'Authorization':'Bearer offline-evaluation'},
                                     json={'case':2,'dataset_code':'offline-online'})
        response.raise_for_status()
        sim.closed = True
        answer = response.json()
        schema = Path(__file__).resolve().parents[1] / 'backend/schemas/Case2Answers.json'
        Draft202012Validator(json.loads(schema.read_text()), format_checker=FormatChecker()).validate(answer)
        if sim.auth != ['Bearer offline-evaluation'] * len(sim.auth) or sim.reads != 1:
            raise ValueError('Нарушена изоляция токена или повторно запрошены данные')
        for key in ('stays','requests'):
            if [r['record_id'] for r in answer[key]] != [r['record_id'] for r in sim.data[key]]:
                raise ValueError('Потеря, перестановка или дублирование записей')
        ids = [r['session_id'] for group in answer.values() for r in group]
        if len(set(ids)) != len(ids):
            raise ValueError('Сеансы записей пересекаются')
        for key, kind in [('requests','request'), ('stays','stay')]:
            for item in answer[key]:
                session = sim.sessions[item['session_id']]['session']
                if (session['record_id'], session['kind']) != (item['record_id'], kind):
                    raise ValueError('Ссылка указывает на другую запись или вид сеанса')
        bad = []
        extras = 0
        for item, req in zip(answer['requests'], sim.data['requests'], strict=True):
            kind, wanted = expected[item['record_id']]
            actual = (await upstream.get(f"https://simulator.invalid/room/{item['session_id']}/state",
                                         params={'at':req['at']})).json()['state']
            extras += sum(actual[d][k] != value and wanted[d][k] == value
                          for d, fields in req['initial_state'].items() for k,value in fields.items())
            if actual != wanted or [r['response_class'] for r in item['replies']] != [kind]:
                bad.append(item['record_id'])
        broken = {}
        for item, stay in zip(answer['stays'], sim.data['stays'], strict=True):
            entries = sim.sessions[item['session_id']]['entries']
            steps = next(e['steps'] for e in entries if e['kind'] == 'scenario')
            rules = audit(stay, beds[item['record_id']], steps, sim.data['devices'])
            # R8 задаёт начало ночного режима. Эталонные часы заданы вручную.
            if not any(s['at'] == beds[item['record_id']]['resolved_bedtime_at'] and
                       s['device_id'] == 'light' and s['values'].get('brightness') == 0 for s in steps):
                rules.append('R8')
            if rules:
                broken[item['record_id']] = rules
        c = 1 - len(bad) / len(expected)
        r8_matches = len(beds) - sum('R8' in rules for rules in broken.values())
        s = 1 - sum(rule != 'R8' for rules in broken.values() for rule in rules) / (7 * len(beds))
        return dict(guests=len(beds), requests=len(expected), incorrect_requests=bad, failed_rules=broken,
                    extra_changes=extras, missing=0, r8_matches=r8_matches, C=c, S=s, x=.7*c+.3*s, response_bytes=len(response.content),
                    seconds=round(time.monotonic()-started,3), peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def main():
    with patch.dict(os.environ, FAKE_ENV), block_network():
        report = asyncio.run(verify())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report['failed_rules']) or report['x'] < 1 or report['response_bytes'] > 64_000_000)


if __name__ == '__main__':
    raise SystemExit(main())
