"""Storage failures are NOT successful/definitively rejected device mutations."""
from fastapi.testclient import TestClient

from backend.core import ServiceError
from main import app as backend
from scripts.rehearse_client import build_rehearsal
from tests.helpers import AT


def _open(api):
    result = api.post("/api/v1/sessions", headers={"Authorization": "Bearer offline-team"},
                      json={"source": "dev", "stay_id": "stay_test"})
    assert result.status_code == 201, result.text
    return {"Authorization": "Bearer " + result.json()["session_token"]}


def _device(api, auth, key):
    return api.post("/api/v1/devices",
                    headers={**auth, "Idempotency-Key": key},
                    json={"device_id": "light", "values": {"brightness": 33}, "at": AT})


def test_session_checkpoint_error_prevents_action_post(tmp_path):
    with TestClient(build_rehearsal(persist_path=str(tmp_path / "offline.sqlite3"))) as api:
        auth = _open(api)
        before = api.get("/api/v1/state", headers=auth).json()["state"]
        sim = backend.state.demo_store
        previous = sim.save_session

        def broken_disk(*_):
            raise ServiceError("STORAGE_UNAVAILABLE", "Synthetic disk fault.", 503)

        sim.save_session = broken_disk
        try:
            failed = _device(api, auth, "disk-before-action")
            assert failed.status_code == 503, failed.text
            assert failed.json()["code"] == "STORAGE_UNAVAILABLE"
            assert backend.state.sessions
            assert backend.state.demo_store is sim
        finally:
            sim.save_session = previous
        assert api.get("/api/v1/state", headers=auth).json()["state"] == before
        assert backend.state.sessions
        assert backend.state.demo_store is sim


def test_failed_simulator_fsync_cannot_become_confirmed_success(tmp_path):
    with TestClient(build_rehearsal(persist_path=str(tmp_path / "offline.sqlite3"))) as api:
        auth = _open(api)
        simulator = api.app.state.rehearsal_simulator
        original = simulator.persist_hook

        def broken_device_storage(_sim):
            raise ServiceError("STORAGE_UNAVAILABLE", "Synthetic fsync failed.", 503)

        simulator.persist_hook = broken_device_storage
        try:
            failed = _device(api, auth, "disk-after-action")
            assert failed.status_code == 409, failed.text
            assert failed.json()["code"] == "ACTION_UNCERTAIN"
        finally:
            simulator.persist_hook = original
        session = api.get("/api/v1/session", headers=auth).json()
        assert session["read_only"] is True
        assert session["reconciliation_required"] is True
        assert session["pending_action"]["code"] == "ACTION_UNCERTAIN"
        again = _device(api, auth, "disk-after-action")
        assert again.status_code == 409
        assert again.json()["code"] == "ACTION_UNCERTAIN"
        new = _device(api, auth, "disk-new-action")
        assert new.status_code == 409
        assert new.json()["code"] == "SESSION_READ_ONLY"
