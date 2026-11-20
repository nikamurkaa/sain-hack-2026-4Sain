"""Подтверждение изменений по состоянию и журналу симулятора."""
from copy import deepcopy
from backend.core import ServiceError


class Room:
    def __init__(self, client, session):
        self.client, self.session = client, session
        self.path = "/room/" + session["session_id"]

    @classmethod
    async def create(cls, client, record_id, kind, run_id=None):
        body = {"record_id": record_id, "kind": kind}
        if run_id:
            body["run_id"] = run_id
        session = await client.request("POST", "/room/session", body=body, retry=True)
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

    async def execute(self, commands, at):
        # Все относительные просьбы уже преобразованы в абсолютные значения.
        # При неопределённом результате проверяем состояние, а не повторяем изменение.
        if not commands:
            return await self.state(at)
        # Freeze the entire state at this request's timestamp; changes scheduled at
        # other instants must not be mistaken for action side effects.
        expected = deepcopy(await self.state(at))
        for command in commands:
            try:
                await self.client.request("POST", self.path + "/action", body=command)
            except ServiceError as exc:
                if exc.code != "UPSTREAM_UNCERTAIN":
                    raise
            actual = await self.state(at)
            device = command["device_id"]
            if device not in expected:
                raise ServiceError("ACTION_UNCONFIRMED", "Состояние номера не содержит устройство.")
            expected[device].update(command["values"])
            # Compare EVERY field, including the ones the command must preserve.
            if actual != expected:
                raise ServiceError("ACTION_UNCONFIRMED", "Изменения подтверждены не полностью. Проверьте состояние комнаты.")
        return actual

