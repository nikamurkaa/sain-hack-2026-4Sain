"""Offline API regression: virtual time is a read-only preview, not live state."""
from fastapi.testclient import TestClient
from scripts.rehearse_client import build_rehearsal


def test_explicit_preview_does_not_replace_live_fallback():
    with TestClient(build_rehearsal()) as api:
        opened = api.post('/api/v1/sessions', headers={'Authorization': 'Bearer offline-team'},
                          json={'source': 'dev', 'stay_id': 'stay_test'})
        assert opened.status_code == 201, opened.text
        auth = {'Authorization': 'Bearer ' + opened.json()['session_token']}
        prepared = api.get('/api/v1/prepared', headers=auth).json()
        assert prepared['last_confirmed'] is None
        preview_at = '2026-11-13T00:00:00+03:00'
        preview = api.get('/api/v1/state', params={'at': preview_at}, headers=auth)
        assert preview.status_code == 200, preview.text
        assert preview.json()['at'] == preview_at
        assert api.get('/api/v1/prepared', headers=auth).json()['last_confirmed'] is None
        live = api.get('/api/v1/state', headers=auth)
        assert live.status_code == 200, live.text
        assert live.json()['at'] == opened.json()['at']
        again = api.get('/api/v1/state', params={'at': preview_at}, headers=auth)
        assert again.status_code == 200
        assert api.get('/api/v1/prepared', headers=auth).json()['last_confirmed'] == live.json()
        # Explicit preview of the current instant is also read-only.
        same = api.get('/api/v1/state', params={'at': live.json()['at']}, headers=auth)
        assert same.status_code == 200
        assert api.get('/api/v1/prepared', headers=auth).json()['last_confirmed'] == live.json()


def test_profile_does_not_fabricate_display_name():
    with TestClient(build_rehearsal()) as api:
        opened = api.post('/api/v1/sessions', headers={'Authorization': 'Bearer offline-team'},
                          json={'source': 'dev', 'stay_id': 'stay_test'})
        auth = {'Authorization': 'Bearer ' + opened.json()['session_token']}
        profile = api.get('/api/v1/guest', headers=auth).json()['profile']
        assert 'display_name' not in profile  # Not part of official Case2Dataset schema.
