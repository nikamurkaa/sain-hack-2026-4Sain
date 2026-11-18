import asyncio
from copy import deepcopy
from datetime import timedelta
import pytest
from jsonschema.exceptions import ValidationError
from backend.core import evidence, moment, validate_schema, default_state
from backend.preferences import parse_facts, PreferenceResolver
from backend.scheduler import bedtime, build_scenario
from backend.commands import plan_commands, Refusal
from backend.intents import Intent
from tests.helpers import AT, WAKE, CATALOG, dataset, prefs, FakeModel


def test_synthetic_dataset_valid():
    validate_schema('Case2Dataset',dataset())

@pytest.mark.parametrize('value',['2026-11-12T20:00:00Z','2026-11-12T20:00:00','2026-11-12','x'])
def test_time_requires_offset(value):
    with pytest.raises(ValueError):moment(value)


def test_history_is_scoped_and_bounded():
    d=dataset()
    d['chat_history']=[{'user_id':u,'role':role,'at':at,'message_id':'same','text':'sample'} for u,role,at in
       [('guest_test','user',AT),('other','user',AT),('guest_test','agent',AT),('guest_test','user',WAKE)]]
    d['events']=[{'user_id':'guest_test','started_at':AT,'ended_at':WAKE,'event_id':'future','payload':{'text':'later'}}]
    assert len(evidence(d,'guest_test',AT))==1


def test_invalid_evidence_rejected():
    fact={'key':'temperature','value':'warm','source_id':'missing','quote':'warm'}
    with pytest.raises(ValueError):parse_facts({'facts':[fact]},[],CATALOG['devices'],CATALOG['tracks'])


def test_invented_quote_rejected():
    hist=[{'id':'m1','text':'прохладно','at':AT}]
    fact={'key':'temperature','value':'warm','source_id':'m1','quote':'тепло'}
    with pytest.raises(ValueError):parse_facts({'facts':[fact]},hist,CATALOG['devices'],CATALOG['tracks'])


def test_cache_and_no_reference():
    async def run():
        d=dataset();d['reference']={'secret':'do not use'}
        model=FakeModel();resolver=PreferenceResolver(d,model)
        first=await resolver.resolve('guest_test',AT,'2026-11-11')
        first['tracks'].append('corruption')
        second=await resolver.resolve('guest_test',AT,'2026-11-11')
        assert second['tracks']==[] and model.calls==1
    asyncio.run(run())

@pytest.mark.parametrize('zone,hour',[('Europe/Moscow',23),('Asia/Novosibirsk',20),('Europe/London',1)])
def test_timezone_rule(zone,hour):
    d=dataset();d['users'][0]['timezone']=zone
    assert bedtime(d['users'][0],d['stays'][0]).hour==hour


def state_at(steps, at):
    state=default_state(CATALOG['devices'])
    for step in steps:
        if moment(step['at'])<=moment(at):state[step['device_id']].update(step['values'])
    return state

@pytest.mark.parametrize('temp,expected',[('cool',17.5),('neutral',19.5),('warm',21.5)])
def test_night_and_dawn_rules(temp,expected):
    d=dataset();p=prefs();p.update(temperature=temp,tracks=['track_04'],timer=30,alarm_mode='light')
    steps=build_scenario(d['users'][0],d['stays'][0],p,d['devices'],d['sleep_rules'])
    evening=state_at(steps,'2026-11-12T22:30:00+03:00')
    assert 10<=evening['light']['brightness']<=30 and evening['light']['color_temperature_k']<=2700
    night=state_at(steps,'2026-11-12T23:05:00+03:00')
    assert night['light']['brightness']==0 and night['curtains']['position']<=10
    assert night['climate']['temperature_c']==expected and night['dnd']['enabled']
    assert night['sound']['volume']>0 and night['sound']['track_id']=='track_04'
    assert state_at(steps,'2026-11-12T23:36:00+03:00')['sound']['volume']==0
    alarm=state_at(steps,'2026-11-13T06:29:00+03:00')['alarm']
    assert alarm['mode']=='light' and alarm['at']==WAKE
    rises=[s for s in steps if s['device_id']=='light' and s['values'].get('brightness',0)>0 and moment(s['at'])>moment('2026-11-12T23:00:00+03:00')]
    assert len(rises)>=3 and moment(WAKE)-moment(rises[0]['at'])==timedelta(minutes=30)


def test_late_arrival_evening_starts_at_arrival():
    d=dataset();d['stays'][0]['check_in_at']='2026-11-12T22:40:00+03:00'
    steps=build_scenario(d['users'][0],d['stays'][0],prefs(),d['devices'],d['sleep_rules'])
    assert steps[0]['at']==d['stays'][0]['check_in_at']
    assert state_at(steps,steps[0]['at'])['light']['brightness']==20

@pytest.mark.parametrize('name,device,field,expected',[('warmer','climate','temperature_c',24),('cooler','climate','temperature_c',22),
 ('brighter','light','brightness',90),('dimmer','light','brightness',50),('quieter','sound','volume',10)])
def test_relative_command(name,device,field,expected):
    state=default_state(CATALOG['devices']);before=deepcopy(state)
    commands=plan_commands(Intent(intent=name),state,prefs(),AT,CATALOG['devices'],CATALOG['tracks'])
    assert commands==[{'device_id':device,'values':{field:expected},'at':AT}] and state==before

@pytest.mark.parametrize('name,value',[('warmer',15),('cooler',27),('brighter',150),('curtains',-1)])
def test_invalid_value_refused(name,value):
    with pytest.raises(Refusal):plan_commands(Intent(intent=name,value=value),default_state(CATALOG['devices']),prefs(),AT,CATALOG['devices'],CATALOG['tracks'])

@pytest.mark.parametrize('name',['medical','out_of_scope','invalid_value','like_home','like_yesterday','sound_on'])
def test_refusals_do_not_mutate(name):
    state=default_state(CATALOG['devices']);before=deepcopy(state)
    with pytest.raises(Refusal):plan_commands(Intent(intent=name),state,prefs(),AT,CATALOG['devices'],CATALOG['tracks'])
    assert state==before

@pytest.mark.parametrize('name,kwargs',[('all_off',{}),('curtains',{'value':0}),('alarm_set',{'time':'06:30'}),('alarm_cancel',{}),
 ('going_to_bed',{}),('woke_up',{}),('do_not_disturb',{})])
def test_other_commands(name,kwargs):
    assert plan_commands(Intent(intent=name,**kwargs),default_state(CATALOG['devices']),prefs(),AT,CATALOG['devices'],CATALOG['tracks'])


def test_alarm_shift_keeps_mode_and_uses_existing_date():
    state=default_state(CATALOG['devices']);state['alarm'].update(at=WAKE,mode='light')
    commands=plan_commands(Intent(intent='alarm_shift',delta=-15),state,prefs(),AT,CATALOG['devices'],CATALOG['tracks'])
    assert commands[0]['values']=={'at':'2026-11-13T06:45:00+03:00'}


def test_exact_home_fields_only():
    p=prefs();p['home']={'light':{'brightness':33},'climate':{'temperature_c':18}}
    c=plan_commands(Intent(intent='like_home'),default_state(CATALOG['devices']),p,AT,CATALOG['devices'],CATALOG['tracks'])
    assert len(c)==2 and c[0]['values']=={'brightness':33}


def test_all_off_preserves_alarm_timer_and_climate():
    state=default_state(CATALOG['devices'])
    c=plan_commands(Intent(intent='all_off'),state,prefs(),AT,CATALOG['devices'],CATALOG['tracks'])
    assert {x['device_id']:x['values'] for x in c}=={'light':{'brightness':0},'sound':{'volume':0}}


def test_sound_on_preserves_timer():
    p=prefs();p['tracks']=['track_04']
    state=default_state(CATALOG['devices'])
    c=plan_commands(Intent(intent='sound_on'),state,p,AT,CATALOG['devices'],CATALOG['tracks'])
    assert 'timer_minutes' not in c[0]['values'] and c[0]['values']['volume']>state['sound']['volume']


def test_alarm_set_preserves_mode_without_explicit_request():
    state=default_state(CATALOG['devices'])
    p=prefs();p['alarm_mode']='light'
    c=plan_commands(Intent(intent='alarm_set',time='07:00'),state,p,AT,CATALOG['devices'],CATALOG['tracks'])
    assert c[0]['values']=={'at':WAKE}


def test_waking_does_not_touch_sound_or_curtains_without_preference():
    p=prefs();p['morning']={'light':{'brightness':50,'color_temperature_k':3000}}
    c=plan_commands(Intent(intent='woke_up'),default_state(CATALOG['devices']),p,AT,CATALOG['devices'],CATALOG['tracks'])
    assert {x['device_id'] for x in c}=={'light','alarm','dnd'}


def test_timezone_conversion_below_threshold():
    d=dataset();d['users'][0]['timezone']='Asia/Yekaterinburg'
    assert bedtime(d['users'][0],d['stays'][0]).hour==21


def test_explicit_time_mode_and_bad_model_fields():
    from pydantic import ValidationError
    for raw in [{'intent':'alarm_set','time':'25:00'},{'intent':'warmer','value':True},{'intent':'all_off','execute_shell':'anything'}]:
        with pytest.raises(ValidationError):Intent.model_validate(raw)


def test_future_note_is_excluded():
    d=dataset();d['events']=[{'user_id':'guest_test','started_at':WAKE,'ended_at':None,'event_id':'later','payload':{'text':'Люблю тепло'}}]
    assert evidence(d,'guest_test',AT)==[]


def test_nonfinite_value_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):Intent(intent='warmer',value=float('nan'))


def test_profile_temperature_overrides_missing_history():
    async def check():
        d=dataset();d['users'][0]['sleep_preferences']={'temperature':'normal','favorite_track_ids':None}
        p=await PreferenceResolver(d,FakeModel()).resolve('guest_test',AT,'2026-11-11')
        assert p['temperature']=='neutral' and p['sources']['temperature']['source']=='profile'
    asyncio.run(check())


def test_independent_sleep_audit_finds_broken_rules():
    from scripts.sleep_audit import audit
    d=dataset();stay=d['stays'][0];p=prefs()
    expected={'resolved_bedtime_at':'2026-11-12T23:00:00+03:00','resolved_preferences':{'temperature':'normal','favorite_track_ids':[],'gentle_alarm':False}}
    steps=build_scenario(d['users'][0],stay,p,d['devices'],d['sleep_rules'])
    assert audit(stay,expected,steps,d['devices'])==[]
    broken=deepcopy(steps)
    broken.append({'at':'2026-11-13T02:00:00+03:00','device_id':'light','values':{'brightness':100}})
    assert 'R6' in audit(stay,expected,broken,d['devices'])
    broken=deepcopy(steps)
    broken.append({'at':'2026-11-13T02:00:00+03:00','device_id':'climate','values':{'temperature_c':26}})
    assert 'R3' in audit(stay,expected,broken,d['devices'])


@pytest.mark.parametrize('text,expected',[
 ('Поменяла лампу в торшере на тёплую и убавила до трети.',2700),
 ('В спальне ночник, тёплый, процентов на десять.',2700),
 ('Холодный свет на полную яркость.',5000),
 ('Не тёплый свет, а обычный.',None),
 ('В комнате холодно. Свет на треть.',None),
])
def test_qualitative_light_has_source(text,expected):
    fact={'key':'home.light.brightness','value':30,'source_id':'e1','quote':text}
    got=parse_facts({'facts':[fact]},[{'id':'e1','at':AT,'text':text}],CATALOG['devices'],CATALOG['tracks'])
    key='home.light.color_temperature_k'
    if expected is None:assert key not in got
    else:
        assert got[key]['value']==expected and got[key]['quote'] in text


def test_short_sound_timer_still_meets_rule_at_plus_five():
    from scripts.sleep_audit import audit
    d=dataset();p=prefs();p.update(tracks=['track_04'],timer=1)
    expected={'resolved_bedtime_at':'2026-11-12T23:00:00+03:00','resolved_preferences':{'temperature':'normal','favorite_track_ids':['track_04'],'gentle_alarm':False}}
    steps=build_scenario(d['users'][0],d['stays'][0],p,d['devices'],d['sleep_rules'])
    assert audit(d['stays'][0],expected,steps,d['devices'])==[]
