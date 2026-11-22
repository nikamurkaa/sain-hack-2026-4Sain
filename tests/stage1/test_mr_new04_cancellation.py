"""Independent RED: cancellation after a real local simulator POST must fail closed.
Never uses official upstream API; only loopback FastAPI TestClient/MockTransport.
"""
import asyncio
import hashlib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from main import app
from scripts.rehearse_client import build_rehearsal

T1 = "2026-11-12T20:00:00+03:00"
T2 = "2026-11-12T20:45:00+03:00"


def guest(api):
    r = api.post("/api/v1/sessions",
                 headers={"Authorization": "Bearer offline-team"},
                 json={"source": "dev", "stay_id": "stay_test"})
    assert r.status_code == 201, r.text
    token = r.json()["session_token"]
    return ({"Authorization": "Bearer " + token},
            app.state.sessions[hashlib.sha256(token.encode()).hexdigest()])


def write(api, auth, endpoint, key, at=T2, body=None):
    if body is None:
        body = ({"at": at, "device_id": "light", "values": {"brightness": 0}}
                if endpoint == "devices" else
                {"at": at, "text": "Проверка частичного выполнения"})
    return api.post("/api/v1/" + endpoint,
                    headers={**auth, "Idempotency-Key": key}, json=body)


@pytest.mark.parametrize("endpoint", ["devices", "messages"])
def test_cancelled_after_accepted_post_is_uncertain_and_temporally_blocked(endpoint):
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        other, _ = guest(api)
        simulator = wrapper.state.rehearsal_simulator
        original = session.room.client.request
        fired = [False]

        async def cancel_after_commit(method, path, **kwargs):
            answer = await original(method, path, **kwargs)
            if method == "POST" and path.endswith("/action") and not fired[0]:
                fired[0] = True
                raise asyncio.CancelledError("injected cancellation AFTER accepted POST")
            return answer

        session.room.client.request = cancel_after_commit
        before = simulator.actions
        first = write(api, auth, endpoint, "cancel-after-accepted-0001")
        assert fired[0] and first.status_code != 200
        assert simulator.actions == before + 1
        actual = api.get("/api/v1/state", headers=auth, params={"at": T2})
        assert actual.status_code == 200
        assert actual.json()["state"]["light"]["brightness"] == 0
        assert len(session.room.operations) == 1
        op, record = next(iter(session.room.operations.items()))
        assert record["status"] == "uncertain" and record["mutation_possible"]
        assert record["attempted_at"] == T2 and record["confirmed_devices"] == []
        assert session.mutation_floor is not None
        assert datetime.fromisoformat(session.mutation_floor).astimezone(timezone.utc) >= (
            datetime.fromisoformat(T2).astimezone(timezone.utc))
        assert session.action_issues[op]["status"] == "uncertain"
        assert not session.action_issues[op]["verified"]
        info = api.get("/api/v1/session", headers=auth).json()
        assert info["reconciliation_required"] is True
        assert info["pending_action"]["operation_id"] == op
        assert info["pending_action"]["attempted_at"] == T2
        repeat = write(api, auth, endpoint, "cancel-after-accepted-0001")
        assert repeat.status_code == 409
        assert repeat.json()["code"] == "ACTION_UNCERTAIN"
        assert repeat.json()["operation_id"] == op
        assert repeat.json()["confirmed_devices"] == []
        assert repeat.json()["attempted_at"] == T2
        changed = write(api, auth, endpoint, "cancel-after-accepted-0001", at=T1)
        assert changed.status_code == 409 and changed.json()["code"] == "IDEMPOTENCY_CONFLICT"
        assert write(api, auth, "devices", "cancel-past-manual-0001", T1).status_code == 409
        assert write(api, auth, "messages", "cancel-past-message-0001", T1).status_code == 409
        assert simulator.actions == before + 1
        assert api.get("/api/v1/reconciliation", headers=other,
                       params={"operation_id": op}).status_code == 404
        checked = api.get("/api/v1/reconciliation", headers=auth, params={"operation_id": op})
        assert checked.status_code == 200, checked.text
        assert checked.json()["status"] == "uncertain"
        assert checked.json()["snapshot"]["at"] == T2
        assert checked.json()["snapshot"]["state"]["light"]["brightness"] == 0
        assert simulator.actions == before + 1
        assert write(api, auth, "devices", "cancel-past-after-0001", T1).status_code == 409
        safe = write(api, auth, "devices", "cancel-future-0001", T2,
                     {"at": T2, "device_id": "light", "values": {"brightness": 30}})
        assert safe.status_code == 200, safe.text
        assert simulator.actions == before + 2


def test_cancelled_before_first_upstream_post_does_not_invent_confirmation():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth, session = guest(api)
        sim = wrapper.state.rehearsal_simulator
        original = session.room.client.request

        async def before_post(method, path, **kwargs):
            if method == "POST" and path.endswith("/action"):
                raise asyncio.CancelledError("before accepted POST")
            return await original(method, path, **kwargs)

        session.room.client.request = before_post
        before = sim.actions
        result = write(api, auth, "devices", "cancel-pre-post-0001")
        assert result.status_code != 200
        assert sim.actions == before
        op, record = next(iter(session.room.operations.items()))
        assert record["status"] == "uncertain"
        assert record["confirmed_devices"] == []
        assert session.action_issues[op]["status"] == "uncertain"
        assert api.get("/api/v1/session", headers=auth).json()["reconciliation_required"] is True
        assert sim.actions == before
