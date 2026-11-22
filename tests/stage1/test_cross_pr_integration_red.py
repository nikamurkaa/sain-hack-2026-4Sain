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


def test_repeated_partial_operation_reports_same_confirmed_steps():
    from tests.stage1.test_partial_operations import FaultySimulator, COMMANDS
    sim = FaultySimulator(fail_post=2)
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "synthetic"})
    async def check():
        codes = []
        for _ in range(2):
            with pytest.raises(ActionFailure) as failed:
                await room.execute(COMMANDS, AT, operation_id="persistent-partial-key")
            codes.append(failed.value.code)
            assert failed.value.confirmed_devices == ["light"]
        assert codes == ["ACTION_PARTIAL", "ACTION_PARTIAL"]
        assert sim.posts == 2, "Replay never reposts any already attempted subcommand"
        assert room.operations["persistent-partial-key"]["status"] == "partial"
    asyncio.run(check())


def test_conflicting_snapshot_records_conflict_not_unknown():
    from tests.stage1.test_partial_operations import FaultySimulator, COMMANDS
    sim = FaultySimulator(drift=True)
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "synthetic"})
    async def check():
        with pytest.raises(ActionFailure) as failed:
            await room.execute(COMMANDS, AT, operation_id="drift-conflict-key")
        assert failed.value.code == "ACTION_CONFLICT"
        assert room.operations["drift-conflict-key"]["status"] == "conflict"
        assert sim.posts == 1
    asyncio.run(check())


def test_double_submit_same_operation_concurrently_posts_once():
    sim = ConcurrentSimulator()
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "synthetic"})
    cmd = [{"device_id": "light", "values": {"brightness": 0}, "at": AT}]
    async def check():
        one, two = await asyncio.gather(
            room.execute(cmd, AT, operation_id="one-command"),
            room.execute(cmd, AT, operation_id="one-command"),
        )
        assert one == two
        assert sim.posts == 1
    asyncio.run(check())
