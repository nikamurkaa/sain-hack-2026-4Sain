"""Independent MR-NEW-01 red repro: future partial effect and temporal recovery.
Only loopback synthetic FastAPI TestClient/MockSimulator. Never calls organizer API.
"""
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from scripts.rehearse_client import build_rehearsal
from main import app


T1 = "2026-11-12T20:00:00+03:00"
T2 = "2026-11-12T20:45:00+03:00"


def new_guest(client):
    reply = client.post("/api/v1/sessions", headers={"Authorization": "Bearer offline-team"},
                        json={"source": "dev", "stay_id": "stay_test"})
    assert reply.status_code == 201, reply.text
    return {"Authorization": "Bearer " + reply.json()["session_token"]}


def submit(client, auth, key, at, text):
    return client.post("/api/v1/messages",
                       headers={**auth, "Idempotency-Key": key},
                       json={"at": at, "text": text})


def test_future_partial_is_distinct_from_last_success_and_unsafe_replay_is_blocked():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth = new_guest(api)
        first = api.get("/api/v1/state", headers=auth)
        assert first.json()["at"] == T1
        assert first.json()["state"]["light"]["brightness"] == 70
        sim = wrapper.state.rehearsal_simulator
        before = sim.actions
        partial = submit(api, auth, "mrnew01-partial-key", T2,
                         "Проверка частичного выполнения")
        assert partial.status_code == 409, partial.text
        payload = partial.json()
        assert payload["code"] == "ACTION_PARTIAL"
        assert payload["confirmed_devices"] == ["light"]
        assert payload["attempted_at"] == T2
        operation = payload["operation_id"]
        assert isinstance(operation, str) and operation
        after = sim.actions
        assert after == before + 1
        assert submit(api, auth, "mrnew01-partial-key", T2,
                      "Проверка частичного выполнения").json() == payload
        assert sim.actions == after
        different = submit(api, auth, "mrnew01-partial-key", T2, "Сделай потише")
        assert different.status_code == 409 and different.json()["code"] == "IDEMPOTENCY_CONFLICT"
        early = submit(api, auth, "mrnew01-early-key", T1, "Сделай попрохладнее")
        assert early.status_code == 409
        assert early.json()["code"] in ("RECOVERY_REQUIRED", "TIME_BACKWARDS")
        manual = api.post("/api/v1/devices",
            headers={**auth, "Idempotency-Key": "mrnew01-manual-old"},
            json={"device_id": "light", "values": {"brightness": 30}, "at": T1})
        assert manual.status_code == 409
        assert sim.actions == after
        old = api.get("/api/v1/state", headers=auth)
        assert old.json()["at"] == T1 and old.json()["state"]["light"]["brightness"] == 70
        future = api.get("/api/v1/state", headers=auth, params={"at": T2})
        assert future.json()["at"] == T2 and future.json()["state"]["light"]["brightness"] == 0
        assert sim.actions == after
        checked = api.get("/api/v1/reconciliation", headers=auth,
                          params={"operation_id": operation})
        assert checked.status_code == 200, checked.text
        data = checked.json()
        assert data["operation_id"] == operation
        assert data["attempted_at"] == T2
        assert data["status"] == "partial"
        assert data["confirmed_devices"] == ["light"]
        assert data["verified"] is True
        assert data["snapshot"]["at"] == T2
        assert data["snapshot"]["state"]["light"]["brightness"] == 0
        assert sim.actions == after
        session = api.get("/api/v1/session", headers=auth).json()
        assert session["at"] == T1  # Partial is never a done turn.
        assert session["next_action_at"] == T2
        assert session["reconciliation_required"] is False
        early_after = submit(api, auth, "mrnew01-early-after", T1, "Сделай попрохладнее")
        assert early_after.status_code == 409 and early_after.json()["code"] == "TIME_BACKWARDS"
        assert sim.actions == after
        later = submit(api, auth, "mrnew01-forward-key", T2, "Сделай попрохладнее")
        assert later.status_code == 200, later.text
        assert later.json()["reply"]["response_class"] == "done"


def test_failed_reconciliation_remains_unverified_and_cross_guest_cannot_view():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth = new_guest(api)
        reply = submit(api, auth, "mrnew01-stale-key", T2,
                       "Проверка частичного выполнения без состояния")
        assert reply.status_code == 409, reply.text
        payload = reply.json()
        assert payload["attempted_at"] == T2
        opid = payload["operation_id"]
        sim = wrapper.state.rehearsal_simulator
        posts = sim.actions
        stale = api.get("/api/v1/reconciliation", headers=auth, params={"operation_id": opid})
        assert stale.status_code in (502, 503, 504), stale.text
        info = api.get("/api/v1/session", headers=auth).json()
        assert info["reconciliation_required"] is True
        blocked = submit(api, auth, "mrnew01-stale-next", T2, "Сделай попрохладнее")
        assert blocked.status_code == 409 and blocked.json()["code"] == "RECOVERY_REQUIRED"
        assert sim.actions == posts
        stranger = new_guest(api)
        other = api.get("/api/v1/reconciliation", headers=stranger, params={"operation_id": opid})
        assert other.status_code == 404
        verified = api.get("/api/v1/reconciliation", headers=auth, params={"operation_id": opid})
        assert verified.status_code == 200, verified.text
        assert verified.json()["snapshot"]["state"]["light"]["brightness"] == 0
        assert sim.actions == posts



def test_equal_at_partial_reconciles_without_rewriting_success_clock():
    wrapper = build_rehearsal()
    with TestClient(wrapper) as api:
        auth = new_guest(api)
        fault = submit(api, auth, "mrnew01-same-at", T1, "Проверка частичного выполнения")
        assert fault.status_code == 409
        assert fault.json()["attempted_at"] == T1
        op = fault.json()["operation_id"]
        reconcile = api.get("/api/v1/reconciliation", headers=auth,
                            params={"operation_id": op})
        assert reconcile.status_code == 200
        assert reconcile.json()["snapshot"]["at"] == T1
        assert reconcile.json()["snapshot"]["state"]["light"]["brightness"] == 0
        assert api.get("/api/v1/session", headers=auth).json()["at"] == T1


def test_partial_across_midnight_and_preview_must_not_unlock_or_overwrite_snapshot():
    later = "2026-11-13T00:15:00+03:00"
    wrapper = build_rehearsal()
    with TestClient(wrapper) as api:
        auth = new_guest(api)
        partial = submit(api, auth, "mrnew01-midnight", later,
                         "Проверка частичного выполнения")
        assert partial.status_code == 409 and partial.json()["attempted_at"] == later
        op = partial.json()["operation_id"]
        sim = wrapper.state.rehearsal_simulator
        posts = sim.actions
        preview = api.get("/api/v1/state", headers=auth, params={"at": later})
        assert preview.status_code == 200 and preview.json()["state"]["light"]["brightness"] == 0
        assert api.get("/api/v1/session", headers=auth).json()["reconciliation_required"] is True
        assert submit(api, auth, "mrnew01-early-midnight", T1, "Сделай попрохладнее").status_code == 409
        assert sim.actions == posts
        checked = api.get("/api/v1/reconciliation", headers=auth, params={"operation_id": op})
        assert checked.status_code == 200
        before = api.get("/api/v1/prepared", headers=auth).json()["last_confirmed"]
        assert before["at"] == later
        subsequent_preview = api.get("/api/v1/state", headers=auth,
                                     params={"at": "2026-11-13T03:30:00+03:00"})
        assert subsequent_preview.status_code == 200
        after = api.get("/api/v1/prepared", headers=auth).json()["last_confirmed"]
        assert after == before, "Virtual preview must never replace reconciled live snapshot"
        assert sim.actions == posts
        forward = submit(api, auth, "mrnew01-midnight-forward", later, "Сделай попрохладнее")
        assert forward.status_code == 200, forward.text


def test_manual_device_uncertain_future_time_must_reconcile_before_new_writes():
    wrapper = build_rehearsal()
    with TestClient(wrapper) as api:
        auth = new_guest(api)
        faults = wrapper.state.rehearsal_faults
        faults["mode"] = "uncertain"
        sim = wrapper.state.rehearsal_simulator
        failed = api.post("/api/v1/devices",
            headers={**auth, "Idempotency-Key": "mrnew01-manual-uncertain"},
            json={"device_id": "light", "values": {"brightness": 0}, "at": T2})
        assert failed.status_code == 409, failed.text
        assert failed.json()["code"] == "ACTION_UNCERTAIN"
        assert failed.json()["attempted_at"] == T2
        posts = sim.actions
        assert posts > 0
        assert api.get("/api/v1/session", headers=auth).json()["reconciliation_required"] is True
        blocked = api.post("/api/v1/devices",
            headers={**auth, "Idempotency-Key": "mrnew01-manual-before"},
            json={"device_id":"light", "values":{"brightness":30}, "at":T1})
        assert blocked.status_code == 409
        assert sim.actions == posts
        op = failed.json()["operation_id"]
        synced = api.get("/api/v1/reconciliation", headers=auth,
                         params={"operation_id": op})
        assert synced.status_code == 200, synced.text
        assert synced.json()["status"] == "uncertain"
        assert synced.json()["confirmed_devices"] == []
        assert synced.json()["snapshot"]["at"] == T2
        assert synced.json()["snapshot"]["state"]["light"]["brightness"] == 0
        assert sim.actions == posts
        restored = api.post("/api/v1/devices",
            headers={**auth, "Idempotency-Key": "mrnew01-manual-forward"},
            json={"device_id":"light", "values":{"brightness":30}, "at":T2})
        assert restored.status_code == 200, restored.text


def test_conflict_status_stays_conflict_after_temporal_snapshot_reconciliation():
    wrapper = build_rehearsal()
    with TestClient(wrapper) as api:
        auth = new_guest(api)
        failed = submit(api, auth, "mrnew01-conflict-future", T2,
                        "Проверка конфликта состояния")
        assert failed.status_code == 409
        assert failed.json()["code"] == "ACTION_CONFLICT"
        opid = failed.json()["operation_id"]
        latest = api.get("/api/v1/reconciliation", headers=auth,
                         params={"operation_id": opid})
        assert latest.status_code == 200, latest.text
        assert latest.json()["status"] == "conflict"
        assert latest.json()["snapshot"]["at"] == T2
        assert api.get("/api/v1/session", headers=auth).json()["history"] == []
        # A confirmed state observation does not retroactively turn conflict
        # into a success or permit a post at the previous 20:00 instant.
        assert submit(api, auth, "mrnew01-conflict-early", T1, "Сделай потише").status_code == 409
