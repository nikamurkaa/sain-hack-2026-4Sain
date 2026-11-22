"""MR-001 real FastAPI + MockTransport REHEARSAL fault injection, no official calls."""
import pytest
from fastapi.testclient import TestClient

from scripts.rehearse_client import build_rehearsal


def open_dev(api):
    result = api.post("/api/v1/sessions", headers={"Authorization": "Bearer offline-team"},
                      json={"source": "dev", "stay_id": "stay_test"})
    assert result.status_code == 201, result.text
    data = result.json()
    return ({"Authorization": "Bearer " + data["session_token"]}, data["at"])


@pytest.mark.parametrize("phrase,code,devices", [
    ("Проверка частичного выполнения", "ACTION_PARTIAL", ["light"]),
    ("Проверка частичного выполнения без состояния", "ACTION_PARTIAL", ["light"]),
    ("Проверка конфликта состояния", "ACTION_CONFLICT", ["light"]),
    ("Проверка неопределённого результата", "ACTION_UNCERTAIN", []),
])
def test_backend_real_http_fault_evidence_replay_and_no_unsafe_post(phrase, code, devices):
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, at = open_dev(api)
        baseline = api.get("/api/v1/state", headers=auth).json()["state"]
        sim = wrapper.state.rehearsal_simulator
        before_posts = sim.actions
        headers = {**auth, "Idempotency-Key": "mr001-fault-replay-0001"}
        body = {"text": phrase, "at": at}
        failed = api.post("/api/v1/messages", headers=headers, json=body)
        assert failed.status_code == 409, failed.text
        payload = failed.json()
        assert payload["code"] == code
        assert isinstance(payload.get("operation_id"), str) and payload["operation_id"]
        assert payload.get("confirmed_devices") == devices
        first_posts = sim.actions
        assert first_posts > before_posts, "First command exercised the REAL local simulator"
        repeated = api.post("/api/v1/messages", headers=headers, json=body)
        assert repeated.status_code == 409 and repeated.json() == payload
        assert sim.actions == first_posts, "Idempotent HTTP replay must never run another POST"
        history = api.get("/api/v1/session", headers=auth).json()["history"]
        assert history == [], "A partial/conflicted/uncertain attempt is not a done turn"
        different = api.post("/api/v1/messages", headers=headers,
                             json={"text": "Сделай потише", "at": at})
        assert different.status_code == 409
        assert different.json()["code"] == "IDEMPOTENCY_CONFLICT"
        # A lost GET is retried safely and may still be unavailable; no action
        # is reissued as part of reconciliation.
        actual = api.get("/api/v1/state", headers=auth)
        if phrase == "Проверка частичного выполнения без состояния":
            assert actual.status_code == 502, actual.text
            assert sim.actions == first_posts
            actual = api.get("/api/v1/state", headers=auth)
        assert actual.status_code == 200, actual.text
        assert actual.json()["state"]["light"]["brightness"] == 0
        assert sim.actions == first_posts
        assert actual.json()["state"]["sound"] == baseline["sound"] if code == "ACTION_PARTIAL" else True
        assert wrapper.state.rehearsal_faults["injected"] == 1
