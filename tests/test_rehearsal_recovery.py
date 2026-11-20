"""Rehearsal recovery test: never persist a guest token across a restart."""
from fastapi.testclient import TestClient
from scripts.rehearse_client import build_rehearsal


def test_restart_requires_new_session_and_can_recover_offline():
    with TestClient(build_rehearsal()) as client:
        opened = client.post('/api/v1/sessions',
            headers={'Authorization': 'Bearer offline-team'},
            json={'source': 'dev', 'stay_id': 'stay_test'})
        assert opened.status_code == 201
        old_token = opened.json()['session_token']
        assert client.get('/api/v1/session', headers={
            'Authorization': 'Bearer ' + old_token}).status_code == 200
    with TestClient(build_rehearsal()) as fresh:
        # No silent or insecure restoration of stale in-memory sessions.
        assert fresh.get('/api/v1/session', headers={
            'Authorization': 'Bearer ' + old_token}).status_code == 401
        assert fresh.get('/health').status_code == 200
        renewed = fresh.post('/api/v1/sessions',
            headers={'Authorization': 'Bearer offline-team'},
            json={'source': 'dev', 'stay_id': 'stay_test'})
        assert renewed.status_code == 201
        auth = {'Authorization': 'Bearer ' + renewed.json()['session_token']}
        assert fresh.get('/api/v1/state', headers=auth).status_code == 200
