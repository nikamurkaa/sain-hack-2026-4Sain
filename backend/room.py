"""Подтверждение изменений по состоянию и журналу симулятора."""
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
        return cls(client, session)

    async def state(self, at):
        return (await self.client.request("GET", self.path + "/state", params={"at": at}, retry=True))["state"]

    async def scenario(self, steps):
        try:
            await self.client.request("POST", self.path + "/scenario", body={"steps": steps})
        except ServiceError as exc:
            if exc.code != "UPSTREAM_UNCERTAIN":
                raise
        log = await self.client.request("GET", self.path + "/log", retry=True)
        scenarios = [e for e in log["entries"] if e["kind"] == "scenario"]
        if not scenarios or scenarios[-1]["steps"] != steps:
            raise ServiceError("SCENARIO_UNCONFIRMED", "Симулятор не подтвердил сохранение расписания.")

    async def execute(self, commands, at):
        # Все относительные просьбы уже преобразованы в абсолютные значения.
        # При неопределённом результате проверяем состояние, а не повторяем изменение.
        for command in commands:
            try:
                await self.client.request("POST", self.path + "/action", body=command)
            except ServiceError as exc:
                if exc.code != "UPSTREAM_UNCERTAIN":
                    raise
            actual = await self.state(at)
            if any(actual[command["device_id"]].get(k) != v for k, v in command["values"].items()):
                raise ServiceError("ACTION_UNCONFIRMED", "Изменения подтверждены не полностью. Проверьте состояние комнаты.")
        return await self.state(at)
