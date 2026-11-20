"""Typed dev-only manual controls confirm simulator state, idempotency, and final denial."""
from fastapi.testclient import TestClient
from scripts.rehearse_client import build_rehearsal
from tests.helpers import AT

def test_six_manual_devices_confirmed_and_idempotent():
    with TestClient(build_rehearsal()) as api:
        opened=api.post('/api/v1/sessions',headers={'Authorization':'Bearer offline-team'},
                        json={'source':'dev','stay_id':'stay_test'})
        assert opened.status_code==201, opened.text
        auth={'Authorization':'Bearer '+opened.json()['session_token']}
        settings=[('climate','temperature_c',21),('light','brightness',38),
                  ('curtains','position',65),('sound','volume',42),
                  ('sound','track_id','track_04'),('alarm','at','06:40'),
                  ('dnd','enabled',True)]
        for i,(device,field,value) in enumerate(settings):
            body={'device_id':device,'values':{field:value},'at':AT}
            if device=='alarm': body['values']['mode']='both'
            headers={**auth,'Idempotency-Key':f'manual-setting-{i}'}
            response=api.post('/api/v1/devices',headers=headers,json=body)
            assert response.status_code==200,(device,response.text)
            data=response.json()
            assert data['reply']['response_class']=='done'
            assert str(value) in str(data['state'][device][field])
            assert api.post('/api/v1/devices',headers=headers,json=body).json()==data
            assert api.post('/api/v1/devices',headers=headers,json={**body,'values':{field:False}}).status_code==409
            state=api.get('/api/v1/state',headers=auth).json()['state']
            assert state[device][field]==data['state'][device][field]
        assert api.post('/api/v1/devices',headers={**auth,'Idempotency-Key':'invalid-temp'},
            json={'device_id':'climate','values':{'temperature_c':35},'at':AT}).status_code==422
        assert api.post('/api/v1/devices',headers={**auth,'Idempotency-Key':'invalid-field'},
            json={'device_id':'climate','values':{'__proto__':3},'at':AT}).status_code==422
        assert len(api.get('/api/v1/session',headers=auth).json()['history'])==len(settings)

def test_final_cannot_use_manual_controls():
    with TestClient(build_rehearsal()) as api:
        opened=api.post('/api/v1/sessions',headers={'Authorization':'Bearer offline-team'},
                        json={'source':'final'})
        assert opened.status_code==201,opened.text
        headers={'Authorization':'Bearer '+opened.json()['session_token'],
                 'Idempotency-Key':'final-manual-request'}
        r=api.post('/api/v1/devices',headers=headers,
                   json={'device_id':'light','values':{'brightness':30},'at':opened.json()['at']})
        assert r.status_code==409
        assert r.json()['code']=='SESSION_READ_ONLY'
