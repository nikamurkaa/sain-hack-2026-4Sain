import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from main import app
from tests.helpers import AT, FakeModel
from tests.simulator import Simulator


def test_late_defense_isolates_prepared_final_from_interactive_dev(monkeypatch):
    final, dev = Simulator(), Simulator()
    final.data['meta']['phase'] = 'final'
    final.data['requests'] = []
    final.data['users'][0]['user_id'] = final.data['stays'][0]['user_id'] = 'final_guest'
    final.data['users'][0]['weekday_bedtime'] = '22:30'
    # Совпадение record_id между наборами не даёт права подменять гостя.
    assert final.data['stays'][0]['record_id'] == dev.data['stays'][0]['record_id']
    calls = []
    live_access = True

    def transport(request):
        token = request.headers['authorization']
        calls.append((token, request.url.path))
        if token == 'Bearer evaluation':
            if not live_access and request.url.path.endswith('/state'):
                return httpx.Response(403, json={'code':'RUN_EXPIRED'})
            return final(request)
        assert token == 'Bearer offline-team'
        return dev(request)

    clock = [time.monotonic()]
    controlled_time = SimpleNamespace(monotonic=lambda:clock[0], time=time.time)
    monkeypatch.setattr('main.time', controlled_time)
    monkeypatch.setattr('backend.runner.time', controlled_time)
    team = {'Authorization':'Bearer offline-team'}
    with TestClient(app) as client:
        upstream = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        app.state.http, app.state.model = upstream, FakeModel()
        try:
            response = client.post('/run', headers={'Authorization':'Bearer evaluation'},
                                   json={'case':2,'dataset_code':'official-final'})
            assert response.status_code == 200 and set(response.json()) == {'requests','stays'}
            final.closed = True
            clock[0] += 4 * 3600
            def connect(source):
                result = client.post('/api/v1/sessions', headers=team, json={'source':source,'stay_id':'stay_test'})
                assert result.status_code == 201, result.text
                return result.json(), {'Authorization':'Bearer '+result.json()['session_token']}
            info, headers = connect('final')
            assert info['source'] == 'final' and info['read_only'] and not info['can_send_requests']
            before = client.get('/api/v1/prepared',headers=headers).json()
            assert before['last_confirmed'] is None and before['guest']['user_id'] == 'final_guest'
            assert before['provenance'] == 'prepared' and before['scenario']['steps']
            assert before['guest']['profile']['weekday_bedtime'] == '22:30'
            live = client.get('/api/v1/state', headers=headers).json()
            live_access = False
            assert client.get('/api/v1/state',headers=headers).status_code == 403
            n = len(calls)
            assert client.get('/api/v1/prepared',headers=headers).json()['last_confirmed'] == live
            assert client.get('/api/v1/session',headers=headers).json()['connection_status'] == 'access_ended'
            assert client.post('/api/v1/messages',headers={**headers,'Idempotency-Key':'final-only'},
                               json={'text':'Теплее','at':AT}).status_code == 409
            assert client.post('/api/v1/transcriptions',headers=headers,content=b'a').status_code == 409
            assert len(calls) == n and final.actions == 0
            # Новый клиентский доступ не продлевает upstream-права.
            clock[0] += 1801
            assert client.get('/api/v1/guest',headers=headers).status_code == 401
            _, again = connect('final')
            assert client.get('/api/v1/prepared',headers=again).json()['scenario'] == before['scenario']
            assert client.get('/api/v1/state',headers=again).status_code == 403
            info, dh = connect('dev')
            assert info['source'] == 'dev' and info['can_send_requests']
            assert client.get('/api/v1/guest',headers=dh).json()['user_id'] == 'guest_test'
            sent = {**dh,'Idempotency-Key':'dev-message'}
            body = {'text':'Теплее','at':AT}
            result = client.post('/api/v1/messages',headers=sent,json=body)
            assert result.status_code == 200 and dev.actions == 1
            restored = client.get('/api/v1/session',headers=dh).json()
            assert len(restored['history']) == 1 and restored['history'][0]['utterances'] == ['Теплее']
            assert client.post('/api/v1/messages',headers=sent,json=body).json() == result.json()
            assert dev.actions == 1 and final.actions == 0 and len(dev.runs) == 1 and not final.runs
            assert client.get('/api/v1/prepared',headers=again).json()['guest']['user_id'] == 'final_guest'
            clock[0] += 2701
            assert client.get('/api/v1/session',headers=dh).status_code == 401
        finally:
            client.portal.call(upstream.aclose)


def test_upstream_deadline_limits_dev_and_throttling_preserves_dialog(monkeypatch):
    sim = Simulator()
    blocked = True
    def proxy(req):
        if req.url.path == '/runs':
            data = sim(req).json()
            data['expires_at'] = (datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat()
            return httpx.Response(201,json=data)
        if blocked and req.url.path.endswith('/action'):
            return httpx.Response(429,json={})
        return sim(req)

    with TestClient(app) as client:
        upstream = httpx.AsyncClient(transport=httpx.MockTransport(proxy))
        app.state.http,app.state.model = upstream,FakeModel()
        try:
            def connect():
                r = client.post('/api/v1/sessions',headers={'Authorization':'Bearer offline-team'},
                                json={'source':'dev','stay_id':'stay_test'})
                assert r.status_code == 201
                assert 0 < r.json()['expires_in'] <= 90
                return {'Authorization':'Bearer '+r.json()['session_token']}
            headers = connect()
            def send(key):
                return client.post('/api/v1/messages',headers={**headers,'Idempotency-Key':key},
                                   json={'text':'Теплее','at':AT})
            assert send('limited-once').status_code == 429
            status = client.get('/api/v1/session',headers=headers).json()
            assert status['connection_status'] == 'rate_limited' and status['history'] == [] and sim.actions == 0
            blocked = False
            assert send('user-confirmed').status_code == 200
            sim.closed = True
            assert send('now-closed').status_code == 409
            status = client.get('/api/v1/session',headers=headers).json()
            assert status['source']=='dev' and status['read_only'] and not status['can_send_requests']
            assert len(status['history']) == sim.actions == 1
            assert send('no-replay').status_code == 409
            sim.closed = False
            new = connect()
            assert client.get('/api/v1/session',headers=new).json()['history'] == []
            assert len(sim.runs) == 2 and sim.actions == 1
        finally:
            client.portal.call(upstream.aclose)
