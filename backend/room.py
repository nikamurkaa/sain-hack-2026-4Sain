"""Подтверждение изменений по состоянию и журналу симулятора."""
from copy import deepcopy
import asyncio
import hashlib
import json
from uuid import uuid4
from backend.core import ServiceError


class ActionFailure(ServiceError):
    """Confirmed steps are explicit; an unknown step must never be called done."""

    def __init__(self, code, message, operation_id, confirmed_devices):
        super().__init__(code, message, 409)
        self.operation_id = operation_id
        self.confirmed_devices = list(confirmed_devices)


class Room:
    def __init__(self, client, session):
        self.client, self.session = client, session
        self.path = "/room/" + session["session_id"]
        # In-memory, per-upstream-session diagnostic journal. Restart durability
        # is intentionally NOT promised until an authorized persistent contract.
        self.operations = {}
        # Serializes read -> POST -> full-state reconciliation per Room instance.
        self._execute_lock = asyncio.Lock()

    @classmethod
    async def create(cls, client, record_id, kind, run_id=None):
        body = {"record_id": record_id, "kind": kind}
        if run_id:
            body["run_id"] = run_id
        # A lost response to POST /room/session is not safely retryable.
        session = await client.request("POST", "/room/session", body=body)
        if not isinstance(session.get("session_id"), str) or not isinstance(session.get("initial_state"), dict):
            raise ServiceError("UPSTREAM_FORMAT", "Симулятор вернул некорректный сеанс.")
        return cls(client, session)

    async def state(self, at):
        result = await self.client.request("GET", self.path + "/state", params={"at": at}, retry=True)
        state = result.get("state")
        if not isinstance(state, dict) or not all(isinstance(fields, dict) for fields in state.values()):
            raise ServiceError("UPSTREAM_FORMAT", "Симулятор вернул некорректное состояние.")
        initial = self.session.get("initial_state", {})
        if any(device not in state or fields.keys() - state[device].keys() for device, fields in initial.items()):
            raise ServiceError("UPSTREAM_FORMAT", "Состояние номера содержит не все настройки.")
        return state

    async def scenario(self, steps):
        try:
            await self.client.request("POST", self.path + "/scenario", body={"steps": steps})
        except ServiceError as exc:
            if exc.code != "UPSTREAM_UNCERTAIN":
                raise
        log = await self.client.request("GET", self.path + "/log", retry=True)
        entries = log.get("entries")
        if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
            raise ServiceError("UPSTREAM_FORMAT", "Симулятор вернул некорректный журнал.")
        scenarios = [entry for entry in entries if entry.get("kind") == "scenario"]
        if not scenarios or scenarios[-1].get("steps") != steps:
            raise ServiceError("SCENARIO_UNCONFIRMED", "Симулятор не подтвердил сохранение расписания.")

    async def execute(self, commands, at, operation_id=None):
        # Local session boundaries serialize same-room commands; /run records
        # continue to use independent Room instances for parallel guests.
        async with self._execute_lock:
            return await self._execute_locked(commands, at, operation_id)

    async def _execute_locked(self, commands, at, operation_id=None):
        """Safely execute an ordered saga, never pretending upstream is atomic.

        POST /action is not blindly retried. Each acknowledged action is checked
        against the *entire* state, including fields which must not change.
        Ambiguous outcomes are reconciled with GET state at the same instant.
        """
        if not commands:
            return await self.state(at)
        operation_id = operation_id or uuid4().hex
        fingerprint = hashlib.sha256(
            json.dumps({"at": at, "commands": commands}, sort_keys=True).encode()
        ).hexdigest()
        earlier = self.operations.get(operation_id)
        if earlier is not None:
            if earlier["fingerprint"] != fingerprint:
                raise ServiceError("IDEMPOTENCY_CONFLICT",
                                   "Идентификатор операции уже использован для других действий.", 409)
            if earlier["status"] == "done":
                return deepcopy(earlier["state"])
            raise ActionFailure("ACTION_UNCERTAIN",
                                "Исход предыдущей операции не подтверждён. Повтор не выполнялся.",
                                operation_id, earlier["confirmed_devices"])

        if len(self.operations) >= 100:
            # Dropping old operation IDs would turn a replay into another POST.
            # Fail closed until session expiry / a supported durable journal.
            raise ServiceError("OPERATION_LIMIT",
                               "Журнал операций заполнен. Создайте новую демосессию.", 429)
        record = {
            "fingerprint": fingerprint,
            "status": "in_progress",
            "confirmed_devices": [],
            "state": None,
            "requested_steps": len(commands),
        }
        self.operations[operation_id] = record

        def fail(code, status, message):
            record["status"] = status
            raise ActionFailure(code, message, operation_id, record["confirmed_devices"])

        try:
            expected = deepcopy(await self.state(at))
        except ServiceError:
            # No POST has happened, but the completed read is not confirmed.
            record["status"] = "uncertain"
            raise

        for command in commands:
            device = command["device_id"]
            if device not in expected:
                fail("ACTION_CONFLICT", "uncertain",
                     "Состояние номера не содержит устройство; изменения не подтверждены.")
            desired = deepcopy(expected)
            desired[device].update(command["values"])

            try:
                await self.client.request("POST", self.path + "/action", body=command)
            except ServiceError as exc:
                if exc.code != "UPSTREAM_UNCERTAIN":
                    if record["confirmed_devices"]:
                        names = ", ".join(record["confirmed_devices"])
                        fail("ACTION_PARTIAL", "partial",
                             "Подтверждено частичное выполнение (" + names +
                             "). Остальные изменения не подтверждены.")
                    record["status"] = "failed"
                    raise
                # The external POST might already have committed: do not retry.
                uncertain_post = True
            else:
                uncertain_post = False

            try:
                actual = await self.state(at)
            except ServiceError:
                fail("ACTION_UNCERTAIN", "uncertain",
                     "После действия состояние не удалось прочитать. "
                     "Изменения не подтверждены; повтор не выполнялся.")

            if actual != desired:
                if uncertain_post:
                    fail("ACTION_UNCERTAIN", "uncertain",
                         "Ответ действия потерян, а состояние не подтвердило результат. "
                         "Изменения не подтверждены; повтор не выполнялся.")
                fail("ACTION_CONFLICT", "uncertain",
                     "Состояние номера изменилось иначе ожидаемого. "
                     "Не все изменения подтверждены; дальнейшие действия остановлены.")

            record["confirmed_devices"].append(device)
            record["state"] = deepcopy(actual)
            expected = actual

        record["status"] = "done"
        return deepcopy(expected)
