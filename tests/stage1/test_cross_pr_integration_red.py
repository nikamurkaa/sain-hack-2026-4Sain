"""Stage 1 integrated cross-PR red regression: do not weaken these oracles."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.core import ServiceError
from backend.room import ActionFailure, Room
from main import app
from tests.helpers import AT
from tests.test_integration import insert_session


def test_idempotent_http_error_repeat_keeps_confirmed_partial_steps():
    with TestClient(app) as api:
        session = insert_session("stage1-guest")
        async def partial(*args, **kwargs):
            raise ActionFailure(
                "ACTION_PARTIAL", "Подтверждено: свет. Остальные не подтверждены.",
                "op-only-synthetic", ["light"])
        session.solution.message = partial
        headers = {"Authorization": "Bearer stage1-guest",
                   "Idempotency-Key": "stage1-error-replay"}
        body = {"text": "Я ложусь", "at": AT}
        first = api.post("/api/v1/messages", headers=headers, json=body)
        second = api.post("/api/v1/messages", headers=headers, json=body)
        assert first.status_code == second.status_code == 409
        assert first.json()["confirmed_devices"] == ["light"]
        assert second.json() == first.json(), "Never erase confirmed steps on retry"
        assert session.history == [], "Failed command is not a successful conversation turn"


class ConcurrentSimulator:
    def __init__(self):
        self.actual = {"light": {"brightness": 50}, "sound": {"volume": 20}}
        self.posts = 0

    async def request(self, method, path, **kwargs):
        if method == "GET":
            await asyncio.sleep(0.01)
            return {"state": deepcopy(self.actual)}
        assert method == "POST" and path.endswith("/action")
        self.posts += 1
        await asyncio.sleep(0.01)
        cmd = kwargs["body"]
        self.actual[cmd["device_id"]].update(cmd["values"])
        return {}


def test_independent_concurrent_commands_do_not_race_on_stale_snapshots():
    sim = ConcurrentSimulator()
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "synthetic"})
    commands = [
        {"device_id": "light", "values": {"brightness": 0}, "at": AT},
        {"device_id": "sound", "values": {"volume": 0}, "at": AT},
    ]
    async def run():
        return await asyncio.gather(
            room.execute([commands[0]], AT, operation_id="independent-light"),
            room.execute([commands[1]], AT, operation_id="independent-sound"),
        )
    results = asyncio.run(run())
    assert sim.posts == 2
    assert all(result == sim.actual for result in results[1:]), "Final operation must see both changes"
    assert room.operations["independent-light"]["status"] == "done"
    assert room.operations["independent-sound"]["status"] == "done"


def test_operation_journal_capacity_must_fail_closed_without_replay_eviction():
    sim = ConcurrentSimulator()
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "synthetic"})
    cmd = [{"device_id": "light", "values": {"brightness": 0}, "at": AT}]
    async def check():
        for i in range(100):
            await room.execute(cmd, AT, operation_id=f"op-{i:03d}")
        posts = sim.posts
        with pytest.raises(ServiceError) as full:
            await room.execute(cmd, AT, operation_id="op-over-limit")
        assert full.value.code == "OPERATION_LIMIT"
        assert sim.posts == posts
        assert await room.execute(cmd, AT, operation_id="op-000") == sim.actual
        assert sim.posts == posts
    asyncio.run(check())
