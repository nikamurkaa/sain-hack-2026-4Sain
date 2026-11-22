"""MR-NEW-04 independent cancellation matrix across real REHEARSAL awaits.

All faults are asyncio.CancelledError (not ServiceError), inserted into the
real MockSimulator HTTP path, while using actual FastAPI endpoints.
"""
import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient
from main import app
from scripts.rehearse_client import build_rehearsal

T1 = "2026-11-12T20:00:00+03:00"
T2 = "2026-11-12T20:45:00+03:00"
MIDNIGHT = "2026-11-13T00:15:00+03:00"


def guest(api):
    response = api.post("/api/v1/sessions",
                        headers={"Authorization": "Bearer offline-team"},
                        json={"source": "dev", "stay_id": "stay_test"})
    assert response.status_code == 201, response.text
    token = response.json()["session_token"]
    return {"Authorization": "Bearer " + token}, app.state.sessions[
        hashlib.sha256(token.encode()).hexdigest()]


def send(api, auth, endpoint, key, at, text=None):
    body = ({"at": at, "device_id": "light", "values": {"brightness": 0}}
            if endpoint == "devices" else
            {"at": at, "text": text or "Проверка отмены составной команды"})
    return api.post("/api/v1/" + endpoint,
                    headers={**auth, "Idempotency-Key": key}, json=body)


@pytest.mark.parametrize("endpoint,point,accepted,known", [
    ("devices", "before_initial_state", 0, []),
    ("devices", "before_first_post", 0, []),
    ("devices", "after_first_post", 1, []),
    ("devices", "before_first_reconcile", 1, []),
    ("devices", "after_first_reconcile", 1, []),
    ("messages", "before_first_post", 0, []),
    ("messages", "after_first_post", 1, []),
    ("messages", "before_first_reconcile", 1, []),
    ("messages", "after_first_reconcile", 1, []),
    ("messages", "before_second_post", 1, ["light"]),
    ("messages", "after_second_post", 2, ["light"]),
    ("messages", "after_final_reconcile", 2, ["light"]),
])
def test_cancellation_at_each_await_is_fail_closed(endpoint, point, accepted, known):
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        simulator = wrapper.state.rehearsal_simulator
        real = session.room.client.request
        post_count = [0]
        fired = [False]

        async def interrupt(method, path, **kwargs):
            is_action = method == "POST" and path.endswith("/action")
            is_state = method == "GET" and path.endswith("/state")
            if not fired[0] and (
                (point == "before_initial_state" and is_state and post_count[0] == 0) or
                (point == "before_first_post" and is_action and post_count[0] == 0) or
                (point == "before_second_post" and is_action and post_count[0] == 1) or
                (point == "before_first_reconcile" and is_state and post_count[0] == 1)
            ):
                fired[0] = True
                raise asyncio.CancelledError("before awaited HTTP operation")
            result = await real(method, path, **kwargs)
            if is_action:
                post_count[0] += 1
            if not fired[0] and (
                (point == "after_first_post" and is_action and post_count[0] == 1) or
                (point == "after_second_post" and is_action and post_count[0] == 2) or
                (point == "after_first_reconcile" and is_state and post_count[0] == 1) or
                (point == "after_final_reconcile" and is_state and post_count[0] == 2)
            ):
                fired[0] = True
                raise asyncio.CancelledError("after awaited HTTP operation")
            return result

        session.room.client.request = interrupt
        before = simulator.actions
        response = send(api, auth, endpoint, "matrix-cancel-key-0001", T2)
        assert fired[0] and response.status_code != 200, response.text
        assert simulator.actions - before == accepted
        assert session.history == [], "Cancellation is never a done turn"
        assert len(session.room.operations) == 1
        opid, record = next(iter(session.room.operations.items()))
        assert record["status"] == "uncertain"
        assert record["confirmed_devices"] == known
        assert record["attempted_at"] == T2
        assert record["mutation_possible"] is (point != "before_initial_state")
        issue = session.action_issues[opid]
        assert issue["status"] == "uncertain" and issue["verified"] is False
        assert issue["confirmed_devices"] == known
        assert issue["attempted_at"] == T2
        if record["mutation_possible"]:
            assert session.mutation_floor == T2
        assert api.get("/api/v1/session", headers=auth).json()["reconciliation_required"] is True
        assert send(api, auth, endpoint, "matrix-cancel-key-0001", T2).status_code == 409
        assert send(api, auth, "devices", "matrix-block-before-0002", T1).status_code == 409
        assert send(api, auth, "messages", "matrix-block-before-0003", T1).status_code == 409
        assert simulator.actions - before == accepted
        # Reconciliation only READS at the same attempted instant. Unknown
        # steps are not retroactively labeled confirmed.
        resolved = api.get("/api/v1/reconciliation", headers=auth,
                           params={"operation_id": opid})
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["status"] == "uncertain"
        assert resolved.json()["confirmed_devices"] == known
        assert resolved.json()["snapshot"]["at"] == T2
        assert simulator.actions - before == accepted
        if record["mutation_possible"]:
            still_old = send(api, auth, "devices", "matrix-old-after-0004", T1)
            assert still_old.status_code == 409 and still_old.json()["code"] == "TIME_BACKWARDS"


@pytest.mark.parametrize("at", [T2, MIDNIGHT])
def test_cancellation_temporal_floor_survives_midnight_and_invalid_offsets(at):
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        real = session.room.client.request
        async def interrupt(method, path, **kwargs):
            result = await real(method, path, **kwargs)
            if method == "POST" and path.endswith("/action"):
                raise asyncio.CancelledError("after accepted POST")
            return result
        session.room.client.request = interrupt
        simulator = wrapper.state.rehearsal_simulator
        before = simulator.actions
        cancelled = send(api, auth, "devices", "midnight-cancel-0001", at)
        assert cancelled.status_code != 200
        assert simulator.actions == before + 1
        assert session.mutation_floor == at
        old = send(api, auth, "devices", "midnight-old-0002", T1)
        assert old.status_code == 409 and old.json()["code"] == "RECOVERY_REQUIRED"
        bad_offset = send(api, auth, "devices", "midnight-wrong-offset", "2026-11-12T21:45:00+04:00")
        assert bad_offset.status_code == 422 and bad_offset.json()["code"] == "INVALID_TIME"
        assert simulator.actions == before + 1
        operation = next(iter(session.room.operations))
        assert api.get("/api/v1/reconciliation", headers=auth,
                       params={"operation_id": operation}).status_code == 200
        old_again = send(api, auth, "devices", "midnight-too-early", T1)
        assert old_again.status_code == 409 and old_again.json()["code"] == "TIME_BACKWARDS"


def test_cancelled_upstream_then_failed_get_stays_pending_until_success():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        real = session.room.client.request
        async def interrupt(method, path, **kwargs):
            result = await real(method, path, **kwargs)
            if method == "POST" and path.endswith("/action"):
                raise asyncio.CancelledError("accepted, then task cancelled")
            return result
        session.room.client.request = interrupt
        simulator = wrapper.state.rehearsal_simulator
        before = simulator.actions
        assert send(api, auth, "devices", "failed-get-cancel-0001", T2).status_code != 200
        opid = next(iter(session.room.operations))
        wrapper.state.rehearsal_faults["fail_state_reads"] = 3
        failed = api.get("/api/v1/reconciliation", headers=auth, params={"operation_id": opid})
        assert failed.status_code in (502, 503, 504)
        assert api.get("/api/v1/session", headers=auth).json()["reconciliation_required"] is True
        assert send(api, auth, "devices", "failed-get-block-0002", T2).status_code == 409
        assert simulator.actions == before + 1
        success = api.get("/api/v1/reconciliation", headers=auth, params={"operation_id": opid})
        assert success.status_code == 200
        assert success.json()["status"] == "uncertain"
        assert success.json()["snapshot"]["state"]["light"]["brightness"] == 0
        assert simulator.actions == before + 1


def test_expiry_and_two_guest_sessions_do_not_leak_cancelled_operation():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        owner, session = guest(api)
        other, second = guest(api)
        real = session.room.client.request
        async def interrupt(method, path, **kwargs):
            result = await real(method, path, **kwargs)
            if method == "POST" and path.endswith("/action"):
                raise asyncio.CancelledError("cancelled after POST")
            return result
        session.room.client.request = interrupt
        assert send(api, owner, "devices", "expired-cancel-0001", T2).status_code != 200
        opid = next(iter(session.room.operations))
        assert api.get("/api/v1/reconciliation", headers=other,
                       params={"operation_id": opid}).status_code == 404
        assert api.get("/api/v1/session", headers=other).json()["reconciliation_required"] is False
        session.expires = 0
        assert api.get("/api/v1/reconciliation", headers=owner,
                       params={"operation_id": opid}).status_code == 401
        assert send(api, owner, "devices", "expired-attempt-0002", T2).status_code == 401
        assert api.get("/api/v1/session", headers=other).status_code == 200
