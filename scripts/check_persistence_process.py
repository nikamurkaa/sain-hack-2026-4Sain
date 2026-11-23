"""Independent actual-process persistence acceptance for local synthetic demo.

Starts/kills/restarts the real uvicorn subprocess. No official API or paid model
credentials are used. Run: python -m scripts.check_persistence_process
"""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

import httpx

BASE = "http://127.0.0.1:8765"
AT = "2026-11-12T20:00:00+03:00"
ROOT = Path(__file__).resolve().parents[1]
TEAM = {"Authorization": "Bearer offline-team"}
SETTINGS = [
    ("climate", {"temperature_c": 21}),
    ("light", {"brightness": 38}),
    ("sound", {"volume": 42, "track_id": "track_04"}),
    ("curtains", {"position": 65}),
    ("alarm", {"at": "06:40", "mode": "both"}),
    ("dnd", {"enabled": True}),
]


@contextmanager
def dbopen(path):
    """SQLite context managers commit but do NOT close on Windows."""
    connection = sqlite3.connect(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def start(path, crash=None):
    env = dict(os.environ)
    env.pop("SAIN_DEMO_CRASH_PROBE", None)
    env.update(SAIN_DEMO_STATE_DB=str(path), PYTHONUNBUFFERED="1")
    if crash:
        env["SAIN_DEMO_CRASH_PROBE"] = crash
    process = subprocess.Popen([sys.executable, "-m", "scripts.rehearse_client"],
                               cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
    for _ in range(140):
        if process.poll() is not None:
            message = process.stderr.read().decode("utf-8", errors="replace")[-3000:]
            raise AssertionError("Backend startup failed: " + message)
        try:
            with httpx.Client(timeout=.4, trust_env=False) as client:
                if client.get(BASE + "/health").status_code == 200:
                    return process
        except (httpx.HTTPError, OSError):
            time.sleep(.15)
    stop(process)
    raise AssertionError("Server did not become healthy")


def stop(proc, force=False):
    if proc.poll() is None:
        (proc.kill() if force else proc.terminate())
    try:
        proc.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate(timeout=10)


def wait_for_crash(proc, expected):
    try:
        code = proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        stop(proc, True)
        raise AssertionError("Expected crash did not happen")
    assert code == expected, ("Crash probe returned wrong code", code, expected)
    proc.communicate(timeout=5)


def request(method, path, token=None, *, payload=None, key=None, expected=200):
    headers = dict(TEAM if token == "TEAM" else {"Authorization": "Bearer " + token})
    if key:
        headers["Idempotency-Key"] = key
    with httpx.Client(timeout=15, trust_env=False) as http:
        res = http.request(method, BASE + path, headers=headers, json=payload)
    assert res.status_code == expected, (method, path, expected, res.status_code, res.text[:400])
    return res.json() if res.content else None


def issue(source="dev"):
    body = {"source": source}
    if source == "dev":
        body["stay_id"] = "stay_test"
    return request("POST", "/api/v1/sessions", "TEAM", payload=body, expected=201)["session_token"]


def state(token):
    return request("GET", "/api/v1/state", token)["state"]


def apply(token, device, values, key):
    return request("POST", "/api/v1/devices", token,
                   payload={"device_id": device, "values": values, "at": AT},
                   key=key)


def action_count(path, room_id):
    with dbopen(path) as db:
        row = db.execute("SELECT payload FROM demo_simulator WHERE key='dev'").fetchone()
    sessions = json.loads(row[0])["sessions"]
    return sum(item["kind"] == "action" for item in sessions[room_id]["entries"])


def room_id_for(path, token):
    digest = hashlib.sha256(token.encode()).hexdigest()
    with dbopen(path) as db:
        row = db.execute("SELECT payload FROM demo_sessions WHERE token_hash=?", (digest,)).fetchone()
    assert row, "Session hash is not persisted"
    return json.loads(row[0])["room"]["session_id"]


def crash_request(token, key, device="light", value=17):
    try:
        apply(token, device, {"brightness": value}, key)
    except (httpx.HTTPError, OSError):
        return
    raise AssertionError("Crash probe returned a normal success response")


def recovered_pending(token, key, base, path, expected_light, expected_actions):
    session = request("GET", "/api/v1/session", token)
    assert session["reconciliation_required"] and session["pending_action"]
    opid = session["pending_action"]["operation_id"]
    room_id = room_id_for(path, token)
    assert state(token)["light"]["brightness"] == expected_light
    assert action_count(path, room_id) == expected_actions
    same = request("POST", "/api/v1/devices", token,
                   payload={"device_id": "light", "values": {"brightness": base}, "at": AT},
                   key=key, expected=409)
    assert same["code"] == "IDEMPOTENCY_CONFLICT"
    # Replaying the IDENTICAL request never creates a second POST.
    failed = request("POST", "/api/v1/devices", token,
                     payload={"device_id": "light", "values": {"brightness": 17}, "at": AT},
                     key=key, expected=409)
    assert failed["code"] == "ACTION_UNCERTAIN", failed
    assert action_count(path, room_id) == expected_actions
    blocked = request("POST", "/api/v1/devices", token,
                      payload={"device_id": "light", "values": {"brightness": 44}, "at": AT},
                      key=key + "-new", expected=409)
    assert blocked["code"] == "RECOVERY_REQUIRED", blocked
    resolved = request("GET", "/api/v1/reconciliation?operation_id=" + opid, token)
    assert resolved["verified"] is True
    assert request("GET", "/api/v1/session", token)["reconciliation_required"] is False
    assert action_count(path, room_id) == expected_actions


def run():
    with tempfile.TemporaryDirectory(prefix="sain-sqlite-") as directory:
        path = Path(directory) / "local state.sqlite3"
        proc = None
        try:
            # First-run empty DB and two independently authenticated guests.
            proc = start(path)
            a, b, final = issue(), issue(), issue("final")
            baseline_b = state(b)
            receipts = []
            for index, (device, values) in enumerate(SETTINGS):
                receipts.append(apply(a, device, values, "persist-manual-" + str(index)))
            # Actual dialog history & contextual continuation, not just device POST.
            request("POST", "/api/v1/messages", a, key="persist-chat-one",
                    payload={"text": "Сделай попрохладнее", "at": AT})
            before = state(a)
            history = request("GET", "/api/v1/session", a)["history"]
            assert len(history) == 7
            assert state(b) == baseline_b
            assert request("GET", "/api/v1/session", final)["read_only"]
            assert path.is_file()
            with dbopen(path) as db:
                assert db.execute("PRAGMA user_version").fetchone()[0] == 1
                assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.execute("SELECT COUNT(*) FROM demo_sessions").fetchone()[0] == 3
            stop(proc)
            proc = start(path)
            assert state(a) == before
            assert state(b) == baseline_b
            assert request("GET", "/api/v1/session", a)["history"] == history
            assert request("GET", "/api/v1/session", final)["read_only"]
            denied = request("POST", "/api/v1/devices", final,
                             payload={"device_id": "light", "values": {"brightness": 45}, "at": AT},
                             key="readonly-persist", expected=409)
            assert denied["code"] == "SESSION_READ_ONLY"
            same = apply(a, SETTINGS[0][0], SETTINGS[0][1], "persist-manual-0")
            assert same == receipts[0], "Identical replay must return stored receipt"
            context = request("POST", "/api/v1/messages", a,
                              payload={"text": "Ещё немного", "at": AT},
                              key="persist-chat-two")
            assert context["reply"]["response_class"] == "done"
            assert state(a)["climate"]["temperature_c"] < before["climate"]["temperature_c"]
            assert state(b) == baseline_b
            # Explicit closure revokes B token in DB and across another process.
            request("DELETE", "/api/v1/session", b, expected=204)
            stop(proc, force=True)
            proc = start(path)
            request("GET", "/api/v1/session", b, expected=401)
            assert request("GET", "/api/v1/session", a)["history"][-1]["utterances"] == ["Ещё немного"]
            # Expiry persisted as epoch, never as process-local monotonic seconds.
            stop(proc)
            with dbopen(path) as db:
                db.execute("UPDATE demo_sessions SET expires_at=0 WHERE token_hash=?",
                           (hashlib.sha256(final.encode()).hexdigest(),))
            proc = start(path)
            request("GET", "/api/v1/session", final, expected=401)
            assert state(a)["climate"]["temperature_c"] == context["state"]["climate"]["temperature_c"]
            stop(proc)
            # Simulate crash AFTER the durable Room operation completed, but
            # BEFORE the guest-facing response/ack was persisted. The Room
            # ledger must not convert it to a client-confirmed success.
            proc = start(path)
            lost = issue()
            apply(lost, "light", {"brightness": 39}, "persist-receipt-lost")
            room_id = room_id_for(path, lost)
            assert action_count(path, room_id) == 1
            stop(proc)
            digest = hashlib.sha256(lost.encode()).hexdigest()
            with dbopen(path) as db:
                raw = db.execute("SELECT payload FROM demo_sessions WHERE token_hash=?",
                                 (digest,)).fetchone()[0]
                snapshot = json.loads(raw)
                snapshot["messages"]["persist-receipt-lost"]["outcome"] = {
                    "type": "error", "code": "ACTION_UNCERTAIN",
                    "message": "Receipt checkpoint interrupted.", "status": 409}
                snapshot["history"] = []
                db.execute("UPDATE demo_sessions SET payload=? WHERE token_hash=?",
                           (json.dumps(snapshot, ensure_ascii=False), digest))
            proc = start(path)
            pending = request("GET", "/api/v1/session", lost)
            assert pending["reconciliation_required"] is True
            assert pending["pending_action"]["code"] == "ACTION_UNCERTAIN"
            retry = request("POST", "/api/v1/devices", lost, key="persist-receipt-lost",
                            payload={"device_id": "light", "values": {"brightness": 39}, "at": AT},
                            expected=409)
            assert retry["code"] == "ACTION_UNCERTAIN"
            assert action_count(path, room_id) == 1
            denied = request("POST", "/api/v1/devices", lost, key="persist-no-premature-followup",
                             payload={"device_id": "light", "values": {"brightness": 48}, "at": AT},
                             expected=409)
            assert denied["code"] == "RECOVERY_REQUIRED"
            opid = pending["pending_action"]["operation_id"]
            assert request("GET", "/api/v1/reconciliation?operation_id=" + opid, lost)["verified"] is True
            assert action_count(path, room_id) == 1
            stop(proc)
            # Deterministic process exit AFTER WAL reservation but BEFORE action POST.
            proc = start(path, "before_post")
            pre = issue()
            base = state(pre)["light"]["brightness"]
            crash_request(pre, "persist-crash-before")
            wait_for_crash(proc, 73)
            proc = start(path)
            recovered_pending(pre, "persist-crash-before", 99, path, base, 0)
            stop(proc)
            # Deterministic process exit AFTER simulator committed POST but BEFORE receipt.
            proc = start(path, "after_post")
            post = issue()
            crash_request(post, "persist-crash-after")
            wait_for_crash(proc, 74)
            proc = start(path)
            recovered_pending(post, "persist-crash-after", 99, path, 17, 1)
            # Zero silent retries, consistent SQLite, and no raw guest tokens stored.
            with dbopen(path) as db:
                assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                rows = db.execute("SELECT token_hash,payload FROM demo_sessions").fetchall()
                for key_hash, raw in rows:
                    assert len(key_hash) == 64
                    assert a not in raw and post not in raw and pre not in raw
            stop(proc)
            proc = None
            # Corrupted DB must fail closed, never silently replace guest state.
            corrupt = Path(directory) / "corrupt.sqlite3"
            corrupt.write_bytes(b"THIS IS NOT A SQLITE DATABASE")
            env = dict(os.environ, SAIN_DEMO_STATE_DB=str(corrupt))
            bad = subprocess.Popen([sys.executable, "-m", "scripts.rehearse_client"],
                                   cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            try:
                assert bad.wait(timeout=15) != 0
                assert corrupt.read_bytes() == b"THIS IS NOT A SQLITE DATABASE"
            finally:
                stop(bad, True)
            print("PERSISTENCE_PROCESS_ACCEPTANCE: PASS — 6 devices, two guests, "
                  "confirmed receipts, contextual dialogue, final read-only, "
                  "clean/forced restarts, expiry, close, before/after-POST "
                  "crashes, uncertain recovery and no action replay")
        finally:
            if proc is not None:
                stop(proc, True)


if __name__ == "__main__":
    run()
