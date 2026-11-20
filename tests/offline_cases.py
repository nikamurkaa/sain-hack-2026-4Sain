"""Заданные вручную намерения и ожидаемые изменения комнат на синтетических данных."""
from copy import deepcopy
from datetime import datetime, timedelta

from tests.helpers import AT, WAKE, dataset

# Фраза, ответ модели, ожидаемое изменение относительно начального состояния.
CASES = [
    ('Добавь света', {'intent':'brighter'}, {'light':{'brightness':90}}),
    ('Убавь свет', {'intent':'dimmer'}, {'light':{'brightness':50}}),
    ('Зябко', {'intent':'warmer'}, {'climate':{'temperature_c':24}}),
    ('Душно', {'intent':'cooler'}, {'climate':{'temperature_c':22}}),
    ('Выключи всё', {'intent':'all_off'}, {'light':{'brightness':0}, 'sound':{'volume':0}}),
    ('Включи дождь', {'intent':'sound_on','track_id':'track_04'}, {'sound':{'volume':30,'track_id':'track_04'}}),
    ('Убавь звук', {'intent':'quieter'}, {'sound':{'volume':10}}),
    ('Закрой шторы', {'intent':'curtains','value':0}, {'curtains':{'position':0}}),
    ('Разбуди в половине седьмого', {'intent':'alarm_set','time':'06:30'}, {'alarm':{'at':'2026-11-13T06:30:00+03:00'}}),
    ('Сдвинь на полчаса позже', {'intent':'alarm_shift','delta':30}, {'alarm':{'at':'2026-11-13T07:30:00+03:00'}}),
    ('Отмени будильник', {'intent':'alarm_cancel'}, {'alarm':{'at':None}}),
    ('Я ложусь', {'intent':'going_to_bed'}, {'light':{'brightness':0},'curtains':{'position':0},'dnd':{'enabled':True}}),
    ('Я проснулся', {'intent':'woke_up'}, {'alarm':{'at':None},'dnd':{'enabled':False},'light':{'brightness':70,'color_temperature_k':4000}}),
    ('Как вчера', {'intent':'like_yesterday'}, {'light':{'brightness':33}}),
    ('Не беспокоить', {'intent':'do_not_disturb'}, {'dnd':{'enabled':True}}),
    ('Как дома', {'intent':'like_home'}, {'climate':{'temperature_c':18}}),
    ('Закажи такси', {'intent':'out_of_scope'}, None),
    ('Поставь 35 градусов', {'intent':'warmer','value':35}, None),
    ('Что выпить для сна?', {'intent':'medical'}, None),
]


class ScriptedModel:
    async def json(self, instruction, payload, output_tokens=3500):
        if 'utterances' in payload:
            words = payload['utterances']
            if words == ['Разбуди меня', 'В половине седьмого']:
                return {'intent':'alarm_set','time':'06:30'}
            if words == ['Ещё немного']:
                previous = payload['history'][-1]['utterances']
                if previous != ['Душно']:
                    raise ValueError('Неверный контекст просьбы')
                return {'intent':'cooler'}
            return next(intent for phrase, intent, _ in CASES if words == [phrase])
        return {'facts': [
            {'key':'home.climate.temperature_c','value':18,'source_id':'chat:home','quote':'Дома 18 градусов'},
            {'key':'yesterday.light.brightness','value':33,'source_id':'chat:yesterday','quote':'Яркость 33'},
        ]}


def fixture():
    d = dataset()
    user, stay, request = (d[key].pop() for key in ('users','stays','requests'))
    expected = {}
    beds = {}
    d['meta']['phase'] = 'online'
    for i in range(10):
        uid, sid = f'guest_{i}', f'stay_{i}'
        temp = ('normal','cool','warm')[i % 3]
        tracks = ['track_04'] if i % 2 else []
        zone, bed = ('Europe/London','2026-11-13T01:00:00+03:00') if i % 2 else ('Europe/Moscow','2026-11-12T23:00:00+03:00')
        profile = dict(temperature=temp, favorite_track_ids=tracks, light_sensitive=None, dislikes=None)
        d['users'].append(dict(user, user_id=uid, timezone=zone, sleep_preferences=profile))
        d['stays'].append(dict(stay, record_id=sid, user_id=uid))
        beds[sid] = dict(resolved_bedtime_at=bed, resolved_preferences=dict(
            temperature=temp, favorite_track_ids=tracks, gentle_alarm=False))
        for mid, text in [('old','Раньше дома ставил 24 градуса'), ('home','Дома 18 градусов'), ('yesterday','Яркость 33')]:
            d['chat_history'].append(dict(message_id=mid, user_id=uid, role='user',
                                         at='2026-11-11T21:00:00+03:00', text=text))
        for j in range(6):
            rid = f'request_{i}_{j}'
            at = (datetime.fromisoformat(AT) + timedelta(minutes=j)).isoformat()
            phrase, intent, delta = CASES[(i*4+j) % len(CASES)]
            words = [phrase]
            if j == 0 and i < 5:
                words, intent, delta = ['Душно'], CASES[3][1], CASES[3][2]
            if j == 1 and i < 5:
                words, intent, delta = ['Ещё немного'], CASES[3][1], CASES[3][2]
            if j == 5:
                words, intent, delta = ['Разбуди меня','В половине седьмого'], CASES[8][1], CASES[8][2]
            initial = deepcopy(request['initial_state'])
            initial['alarm']['at'] = WAKE
            initial['light']['color_temperature_k'] = 3300
            if intent['intent'] == 'going_to_bed':
                delta = dict(delta, climate={'temperature_c':{'normal':19.5,'cool':17.5,'warm':21.5}[temp]},
                             sound={'volume':15,'timer_minutes':30,'track_id':'track_04'} if tracks else {'volume':0})
            d['requests'].append(dict(request, record_id=rid, user_id=uid, stay_id=sid, at=at, initial_state=initial,
                                      utterances=[dict(role='user',at=at,text=text) for text in words]))
            wanted = deepcopy(initial)
            for device, values in (delta or {}).items():
                wanted[device].update(values)
            expected[rid] = ('done' if delta is not None else 'refused', wanted)
    return d, expected, beds
