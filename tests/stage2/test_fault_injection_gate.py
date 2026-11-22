"""Stage 2 fault-injection acceptance gate: FastAPI TestClient + real local MockSimulator.

Every outcome verifies actual upstream POST count and simulator device state;
reconciliation is a GET at the attempted instant, never proof of transaction
atomicity or remote exactly-once delivery. No official endpoint is contacted.
"""
import hashlib
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app
from scripts.rehearse_client import build_rehearsal


T1 = "2026-11-12T20:00:00+03:00"
T2 = "2026-11-12T20:45:00+03:00"


def guest(api):
    response = api.post("/api/v1/sessions",
                        headers={"Authorization": "Bearer offline-team"},
                        json={"source": "dev", "stay_id": "stay_test"})
    assert response.status_code == 201, response.text
    token = response.json()["session_token"]
    return ({"Authorization": "Bearer " + token},
            app.state.sessions[hashlib.sha256(token.encode()).hexdigest()])


def send(api, headers, text, key, at=T2):
    return api.post("/api/v1/messages", headers={**headers, "Idempotency-Key": key},
                    json={"text": text, "at": at})


def actual(api, headers, at=T2):
    result = api.get("/api/v1/state", headers=headers, params={"at":at})
    assert result.status_code == 200, result.text
    return result.json()["state"]


def test_second_device_rejection_is_partial_and_does_not_roll_back_or_repeat_first():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        sim = wrapper.state.rehearsal_simulator
        before = actual(api, auth)
        original_count = sim.actions
        first = send(api, auth, "Проверка частичного выполнения", "stage2-fault-partial-01")
        assert first.status_code == 409
        assert first.json()["code"] == "ACTION_PARTIAL"
        assert first.json()["confirmed_devices"] == ["light"]
        expected = deepcopy(before)
        expected["light"]["brightness"] = 0
        assert actual(api, auth) == expected
        assert sim.actions == original_count + 1
        repeat = send(api, auth, "Проверка частичного выполнения", "stage2-fault-partial-01")
        assert repeat.status_code == 409 and repeat.json() == first.json()
        assert sim.actions == original_count + 1
        assert session.history == []


def test_accepted_post_with_lost_response_is_unsafe_to_retry_and_requires_reconciliation():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        sim = wrapper.state.rehearsal_simulator
        before = actual(api, auth)
        count = sim.actions
        result = send(api, auth, "Проверка неопределённого результата", "stage2-fault-lost-01")
        assert result.status_code == 409, result.text
        assert result.json()["code"] == "ACTION_UNCERTAIN"
        assert result.json()["confirmed_devices"] == []
        assert sim.actions == count + 1  # the simulator accepted the POST
        expected = deepcopy(before)
        expected["light"]["brightness"] = 0
        assert actual(api, auth) == expected
        assert send(api, auth, "Проверка неопределённого результата",
                    "stage2-fault-lost-01").status_code == 409
        altered = send(api, auth, "Я ложусь", "stage2-fault-lost-01")
        assert altered.status_code == 409 and altered.json()["code"] == "IDEMPOTENCY_CONFLICT"
        assert sim.actions == count + 1
        assert session.history == []
        info = api.get("/api/v1/session", headers=auth).json()
        assert info["reconciliation_required"]
        past = send(api, auth, "Я ложусь", "stage2-older-than-commit", at=T1)
        assert past.status_code == 409
        operation_id = info["pending_action"]["operation_id"]
        reconciled = api.get("/api/v1/reconciliation", headers=auth,
                             params={"operation_id": operation_id})
        assert reconciled.status_code == 200, reconciled.text
        assert reconciled.json()["status"] == "uncertain"
        assert reconciled.json()["snapshot"]["state"] == expected
        assert sim.actions == count + 1
        assert send(api, auth, "Я ложусь", "stage2-old-post-reconcile", at=T1).status_code == 409


def test_cancelled_after_accepted_post_preserves_temporal_floor_and_actual_state():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        sim = wrapper.state.rehearsal_simulator
        count = sim.actions
        first = send(api, auth, "Проверка отмены после принятия", "stage2-fault-cancel-01")
        assert first.status_code != 200
        assert sim.actions == count + 1
        op, record = next(iter(session.room.operations.items()))
        assert record["status"] == "uncertain"
        assert record["mutation_possible"] is True
        assert session.mutation_floor == T2
        assert session.action_issues[op]["verified"] is False
        assert send(api, auth, "Проверка отмены после принятия",
                    "stage2-fault-cancel-01").status_code == 409
        assert send(api, auth, "Добавь света", "stage2-cancel-past", at=T1).status_code == 409
        assert sim.actions == count + 1
        # Retry a failed reconciliation read only; NEVER replay the POST.
        possible_read = api.get("/api/v1/reconciliation", headers=auth,
                                params={"operation_id": op})
        assert possible_read.status_code in (200, 502, 503, 504)
        if possible_read.status_code != 200:
            possible_read = api.get("/api/v1/reconciliation", headers=auth,
                                    params={"operation_id": op})
        assert possible_read.status_code == 200
        assert possible_read.json()["snapshot"]["state"]["light"]["brightness"] == 0
        assert sim.actions == count + 1


@pytest.mark.parametrize("body,expected_class", [
    ({"text": "Сделай попрохладнее"}, "prehandler"),
    ({"text": "Сделай попрохладнее", "at": "2026-11-12T21:45:00+04:00"}, "domain"),
])
def test_definitive_422_cannot_commit_any_device(body, expected_class):
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, _ = guest(api)
        sim = wrapper.state.rehearsal_simulator
        before = actual(api, auth)
        posts = sim.actions
        result = api.post("/api/v1/messages", headers={**auth,
                          "Idempotency-Key": "stage2-definitive-422"}, json=body)
        assert result.status_code == 422, result.text
        assert result.headers.get("x-sain-rejection-class") == expected_class
        assert sim.actions == posts
        assert actual(api, auth) == before
        assert api.get("/api/v1/session", headers=auth).json()["reconciliation_required"] is False
        changed = send(api, auth, "Добавь света", "stage2-fresh-after-422")
        assert changed.status_code == 200, changed.text
        assert sim.actions == posts + 1


def test_two_concurrent_same_key_posts_commit_only_once():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        sim = wrapper.state.rehearsal_simulator
        count = sim.actions
        def request(text):
            return send(api, auth, text, "stage2-double-submit-same")
        with ThreadPoolExecutor(max_workers=2) as pool:
            a,b = list(pool.map(request, ["Добавь света", "Добавь света"]))
        assert a.status_code == b.status_code == 200
        assert a.json() == b.json()
        assert sim.actions == count + 1
        assert actual(api, auth)["light"]["brightness"] == 90
        assert len(session.history) == 1
        changed = send(api, auth, "Убавь свет", "stage2-double-submit-same")
        assert changed.status_code == 409 and changed.json()["code"] == "IDEMPOTENCY_CONFLICT"
        assert sim.actions == count + 1
