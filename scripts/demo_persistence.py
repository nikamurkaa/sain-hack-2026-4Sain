"""Crash-safe SQLite checkpoints for the *synthetic loopback demo only*.

Never persist official credentials, provider responses/audio, or external device control.
One local uvicorn process; do not mount this DB on NFS or share between instances.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import threading
import time

from backend.clients import HackClient
from backend.core import ServiceError, moment
from backend.room import ActionFailure, Room
from backend.runner import Solution

SCHEMA_VERSION = 1


def _message_to_json(entry):
    fingerprint, value = entry
    if isinstance(value, ServiceError):
        result = {"type": "error", "code": value.code, "message": value.message, "status": value.status}
        if isinstance(value, ActionFailure):
            result.update({"type": "action", "operation_id": value.operation_id,
                           "confirmed_devices": value.confirmed_devices,
                           "attempted_at": value.attempted_at,
                           "mutation_possible": value.mutation_possible})
    else:
        result = {"type": "result", "data": value}
    return {"fingerprint": fingerprint, "outcome": result}


def _message_from_json(entry):
    value = entry["outcome"]
    if value["type"] == "action":
        result = ActionFailure(value["code"], value["message"], value["operation_id"],
                               value["confirmed_devices"], value.get("attempted_at"),
                               value.get("mutation_possible", True))
    elif value["type"] == "error":
        result = ServiceError(value["code"], value["message"], value["status"])
    elif value["type"] == "result":
        result = value["data"]
    else:
        raise ValueError("Unknown saved message type")
    return entry["fingerprint"], result


class DemoStore:
    def __init__(self, path):
        selected = Path(path).expanduser().absolute()
        if selected.is_symlink():
            raise RuntimeError("Refusing symlink database path")
        self.path = selected.resolve()
        parent_was_missing = not self.path.parent.exists()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path.exists() and not self.path.is_file():
            raise RuntimeError("Database must be a regular file")
        self._lock = threading.RLock()
        # No silent reset for a corrupted DB. Operator must deliberately move it.
        try:
            self.db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
            self.db.execute("PRAGMA busy_timeout=10000")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA secure_delete=ON")
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise RuntimeError("Unsupported demo DB schema; no downgrade or data reset")
            if version == 0:
                with self.transaction():
                    self.db.execute("CREATE TABLE IF NOT EXISTS demo_sessions ("
                                    "token_hash TEXT PRIMARY KEY, expires_at REAL NOT NULL, payload TEXT NOT NULL)")
                    self.db.execute("CREATE TABLE IF NOT EXISTS demo_simulator ("
                                    "key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
                    self.db.execute("PRAGMA user_version=1")
            check = self.db.execute("PRAGMA quick_check").fetchone()[0]
            if check != "ok":
                raise RuntimeError("Demo DB integrity check failed")
            if os.name != "nt":
                # Never chmod an arbitrary existing parent (e.g. /tmp) when
                # an operator supplies a custom SAIN_DEMO_STATE_DB path.
                if parent_was_missing:
                    os.chmod(self.path.parent, 0o700)
                os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
            self.prune()
        except (sqlite3.DatabaseError, OSError) as exc:
            raise RuntimeError("Cannot open valid local demo database; no state was reset") from exc

    @contextmanager
    def transaction(self):
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def prune(self):
        with self.transaction():
            self.db.execute("DELETE FROM demo_sessions WHERE expires_at <= ?", (time.time(),))

    def save_simulator(self, sim):
        # Called synchronously BEFORE any successful synthetic POST response is returned.
        payload = json.dumps({"sessions": sim.sessions, "runs": sim.runs,
                              "until": sim.until}, ensure_ascii=False)
        try:
            with self.transaction():
                self.db.execute("INSERT INTO demo_simulator(key,payload) VALUES('dev',?) "
                                "ON CONFLICT(key) DO UPDATE SET payload=excluded.payload", (payload,))
        except sqlite3.DatabaseError as exc:
            raise ServiceError("STORAGE_UNAVAILABLE", "Не удалось сохранить состояние номера.", 503) from exc

    def restore_simulator(self, sim):
        row = self.db.execute("SELECT payload FROM demo_simulator WHERE key='dev'").fetchone()
        if row:
            saved = json.loads(row[0])
            if not isinstance(saved["sessions"], dict) or not isinstance(saved["runs"], list):
                raise RuntimeError("Invalid synthetic room checkpoint")
            sim.sessions, sim.runs, sim.until = saved["sessions"], saved["runs"], saved["until"]

    def _snapshot(self, session):
        expires_at = time.time() + (session.expires - time.monotonic())
        room = session.room
        return expires_at, {
            "source": "final" if session.presentation else "dev",
            "run_id": session.solution.run_id if session.solution else None,
            "room": room.session,
            "operations": getattr(room, "operations", {}),
            "request_key": getattr(room, "request_key", None),
            "stay": session.stay,
            "prefs": session.prefs,
            "steps": session.steps,
            "at": session.at,
            "read_only": session.read_only,
            "connection_status": session.connection_status,
            "last_confirmed": session.last_confirmed,
            "messages": {k: _message_to_json(v) for k, v in session.messages.items()},
            "history": session.history[-100:],
            "mutation_floor": session.mutation_floor,
            "action_issues": session.action_issues,
        }

    def attach(self, token_hash, session):
        def checkpoint():
            self.save_session(token_hash, session)
        session.persist_hook = checkpoint
        session.room.persist_hook = checkpoint

    def save_session(self, token_hash, session):
        deadline, payload = self._snapshot(session)
        try:
            with self.transaction():
                self.db.execute("INSERT INTO demo_sessions(token_hash,expires_at,payload) VALUES(?,?,?) "
                                "ON CONFLICT(token_hash) DO UPDATE SET "
                                "expires_at=excluded.expires_at,payload=excluded.payload",
                                (token_hash, deadline, json.dumps(payload, ensure_ascii=False)))
        except (sqlite3.DatabaseError, TypeError, ValueError) as exc:
            raise ServiceError("STORAGE_UNAVAILABLE", "Не удалось сохранить гостевой сеанс.", 503) from exc
        # A deterministic subprocess crash probe; deliberately opt-in and
        # synthetic-only, after the WAL reservation is durably committed.
        if os.getenv("SAIN_DEMO_CRASH_PROBE") == "before_post" and any(
            op.get("status") == "in_progress" and not op.get("mutation_possible")
            for op in payload["operations"].values()
        ):
            os._exit(73)

    def delete_session(self, token_hash):
        try:
            with self.transaction():
                self.db.execute("DELETE FROM demo_sessions WHERE token_hash=?", (token_hash,))
        except sqlite3.DatabaseError as exc:
            raise ServiceError("STORAGE_UNAVAILABLE", "Невозможно подтвердить завершение сеанса.", 503) from exc

    def restore_sessions(self, app, sim, model, upstream):
        # Must run AFTER the synthetic final /run bootstrap creates read-only FinalPresentation.
        from main import ClientSession
        self.prune()
        rows = self.db.execute("SELECT token_hash,expires_at,payload FROM demo_sessions").fetchall()
        for token_hash, deadline, raw in rows:
            saved = json.loads(raw)
            if deadline <= time.time():
                self.delete_session(token_hash)
                continue
            source = saved["source"]
            if source == "final":
                view = app.state.final_session
                if view is None or saved["stay"]["record_id"] != view.stay["record_id"]:
                    self.delete_session(token_hash)
                    continue
                solution, room, presentation = None, view.room, view
            elif source == "dev":
                client = HackClient(os.environ["HACK_TEAM_TOKEN"], upstream)
                solution = Solution(sim.data, client, model, saved["run_id"],
                                    time.monotonic() + max(0, deadline - time.time()))
                room = Room(client, saved["room"])
                room.operations = saved["operations"]
                room.request_key = saved.get("request_key")
                if room.session["session_id"] not in sim.sessions:
                    # Never replace missing state with a fresh synthetic room.
                    self.delete_session(token_hash)
                    continue
                presentation = None
            else:
                raise RuntimeError("Unknown stored session source")
            session = ClientSession(
                solution, room, saved["prefs"], saved["steps"], saved["stay"],
                time.monotonic() + max(0, deadline - time.time()),
                saved["at"], read_only=saved["read_only"], presentation=presentation,
            )
            session.connection_status = saved["connection_status"]
            session.last_confirmed = saved["last_confirmed"]
            session.messages = {k: _message_from_json(v) for k, v in saved["messages"].items()}
            session.history = saved["history"]
            session.mutation_floor = saved["mutation_floor"]
            session.action_issues = saved["action_issues"]
            # An in-flight POST may already have reached the simulator when a
            # process crashed. Seal it as UNCERTAIN; never replay automatically.
            for opid, record in getattr(room, "operations", {}).items():
                if record["status"] == "in_progress":
                    record["status"] = "uncertain"
                    record["error"] = (
                        "action", "ACTION_UNCERTAIN",
                        "Процесс завершился до подтверждения операции. Сверьте состояние.", 409,
                    )
                # Recovery may itself have crashed after the Room journal
                # was persisted but before the ClientSession issue was saved.
                if record["status"] not in ("uncertain", "partial", "conflict"):
                    continue
                if opid in session.action_issues:
                    continue  # Do not reopen a previously reconciled issue.
                attempted = record["attempted_at"]
                code = record.get("error", ["action", "ACTION_UNCERTAIN"])[1]
                session.action_issues[opid] = {
                    "code": code, "status": record["status"],
                    "operation_id": opid, "attempted_at": attempted,
                    "confirmed_devices": record.get("confirmed_devices", []),
                    "verified": False,
                }
                if not session.mutation_floor or moment(attempted) > moment(session.mutation_floor):
                    session.mutation_floor = attempted
                request_key = record.get("request_key")
                if request_key in session.messages:
                    fp, previous = session.messages[request_key]
                    if isinstance(previous, ServiceError) or record["status"] == "uncertain":
                        session.messages[request_key] = (
                            fp, ActionFailure(
                                code, "Неизвестен исход операции после аварии; нужна сверка.",
                                opid, record.get("confirmed_devices", []),
                                attempted, record.get("mutation_possible", True)))
            app.state.sessions[token_hash] = session
            self.attach(token_hash, session)
            # Recovery markers themselves are durable across another crash.
            self.save_session(token_hash, session)

    def compact_simulator(self, app, sim):
        """Discard synthetic room logs no longer referenced by valid guest tokens."""
        active = {s.room.session["session_id"] for s in app.state.sessions.values()
                  if s.solution is not None}
        sim.sessions = {sid: record for sid, record in sim.sessions.items() if sid in active}
        # Keep run IDs while any session is alive, avoiding reuse of room identities.
        if not active:
            sim.runs = []
        self.save_simulator(sim)

    def close(self):
        self.db.close()
