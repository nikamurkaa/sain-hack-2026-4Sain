import copy
import json
from pathlib import Path
from backend.core import default_state, moment

CATALOG = json.loads((Path(__file__).parent / 'catalog.json').read_text())
AT = '2026-11-12T20:00:00+03:00'
WAKE = '2026-11-13T07:00:00+03:00'

def dataset():
    schema = json.loads((Path(__file__).parents[1] / 'backend/schemas/Case2Dataset.json').read_text())
    user = dict.fromkeys(schema['properties']['users']['items']['required'])
    user.update(user_id='guest_test', timezone='Europe/Moscow', weekday_bedtime='23:00', weekday_wake_time='07:00')
    state = default_state(CATALOG['devices'])
    return dict(copy.deepcopy(CATALOG), meta={'schema_version':'0.3.0','dataset_id':'case2-dev-v1','case_id':2,
         'phase':'dev','version':'1','generated_at':AT,'history_through':'2026-11-11'}, users=[user],events=[],chat_history=[],
         stays=[{'record_id':'stay_test','user_id':'guest_test','check_in_at':AT,'target_wake_at':WAKE,'hotel_timezone':'Europe/Moscow'}],
         requests=[{'record_id':'request_test','user_id':'guest_test','stay_id':'stay_test','at':AT,'initial_state':state,
                    'utterances':[{'role':'user','at':AT,'text':'Теплее'}]}])

def prefs():
    return {'temperature':'neutral','tracks':[],'volume':15,'timer':30,'alarm_mode':'both',
            'home':{},'morning':{},'yesterday':{},'sources':{},'defaults':[]}

class FakeModel:
    calls=0
    tokens=0
    async def json(self, instruction, payload, output_tokens=3500):
        self.calls += 1
        if 'history' in payload: return {'facts':[]}
        return {'intent':'warmer'}

class FakeRoom:
    def __init__(self):
        self.session={'session_id':'room_test','from':AT,'until':WAKE}
        self.actual=default_state(CATALOG['devices'])
        self.executions=0
    async def state(self, at): return copy.deepcopy(self.actual)
    async def execute(self, commands, at):
        self.executions+=1
        for c in commands:self.actual[c['device_id']].update(c['values'])
        return await self.state(at)
