"""Полная dev-проверка с моделью: python -m scripts.check_dev --with-model.

Использует лимиты команды. Данные и эталон не сохраняются в репозиторий.
Эталон используется только после выполнения решения, в функции compare.
"""
import argparse
import asyncio
import json
import os
import time

import httpx
from backend.clients import HackClient, ModelClient
from backend.core import iso, moment, validate_schema
from backend.runner import Solution
from backend.scheduler import bedtime


def compare(initial, actual, expected):
    errors = []
    touched = set()
    for item in expected['expectations']:
        dev, field = item['device_id'], item['field_id']
        touched.add((dev, field))
        before, after = initial[dev][field], actual[dev][field]
        kind = item['comparison']
        if kind == 'unchanged': ok = before == after
        elif kind == 'increase': ok = after > before
        elif kind == 'decrease': ok = after < before
        elif kind == 'exact': ok = after == item['value']
        elif kind == 'within':
            distance = abs((moment(after)-moment(item['value'])).total_seconds()/60) if item.get('unit') == 'minutes' else abs(after-item['value'])
            ok = distance <= item['tolerance']
        else: raise ValueError('Неизвестный способ сравнения')
        if not ok: errors.append(dev + '.' + field)
    if expected.get('preserve_other_fields'):
        for dev, fields in initial.items():
            for field, value in fields.items():
                if (dev, field) not in touched and actual[dev][field] != value:
                    errors.append(dev + '.' + field + ': изменено лишнее поле')
    return errors


async def check():
    started = time.monotonic()
    async with httpx.AsyncClient(follow_redirects=False) as http:
        client = HackClient(os.environ['HACK_TEAM_TOKEN'], http)
        envelope = await client.request('GET', '/case/2/getData', params={'dataset_code':'case2-dev-v1'}, retry=True)
        data, reference = envelope['dataset'], envelope['reference']
        validate_schema('Case2Dataset', data)
        run = await client.dev_run()
        model = ModelClient(http)
        solution = Solution(data, client, model, run['run_id'])
        answer = await solution.run()
        validation = await client.request('POST', '/case/2/validate', body=answer)
        refs = {r['record_id']:r for r in reference['requests']}
        requests = {r['record_id']:r for r in data['requests']}
        failures = []
        passed = 0
        for item in answer['requests']:
            request, expected = requests[item['record_id']], refs[item['record_id']]
            actual = (await client.request('GET', '/room/'+item['session_id']+'/state', params={'at':request['at']}, retry=True))['state']
            errors = compare(request['initial_state'], actual, expected)
            if [r['response_class'] for r in item['replies']] != expected['expected_reply_classes']:
                errors.append('Класс ответа')
            if errors: failures.append({'record_id':item['record_id'],'errors':errors})
            else: passed += 1
        stays = {s['record_id']:s for s in data['stays']}
        timing_matches = sum(iso(bedtime(solution.user(stays[r['record_id']]['user_id']), stays[r['record_id']])) == r['resolved_bedtime_at'] for r in reference['stays'])
        profile_matches = 0
        for expected in reference['stays']:
            stay = stays[expected['record_id']]
            pref = await solution.prefs(stay['user_id'], stay['check_in_at'])
            actual = {'temperature':{'neutral':'normal'}.get(pref['temperature'],pref['temperature']),
                      'favorite_track_ids':pref['tracks'],'gentle_alarm':pref['alarm_mode']=='light'}
            profile_matches += actual == expected['resolved_preferences']
        report = {'format_valid':validation.get('valid',False), 'requests_passed':passed,
                  'requests_total':len(answer['requests']), 'bedtime_matches':timing_matches,
                  'profile_matches':profile_matches, 'stays_total':len(data['stays']), 'failures':failures,
                  'llm_calls':model.calls,'llm_tokens':model.tokens,'api_calls':client.calls,
                  'seconds':round(time.monotonic()-started,2)}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report['format_valid'] and not failures and profile_matches == len(data['stays']) and timing_matches == len(data['stays'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-model', action='store_true', help='Подтвердить запуск с передачей истории в LLM-прокси организаторов и расходом лимита')
    args = parser.parse_args()
    if not args.with_model: parser.error('Для полного прогона явно укажите --with-model')
    raise SystemExit(0 if asyncio.run(check()) else 1)
