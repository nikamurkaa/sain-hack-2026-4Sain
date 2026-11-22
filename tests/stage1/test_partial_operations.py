"""Stage 1 S-008: fault injection for ordered, non-atomic room actions."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace
import pytest
from backend.core import ServiceError
from backend.room import Room
from tests.helpers import AT

COMMANDS = [
    {"device_id": "light", "values": {"brightness": 0}, "at": AT},
    {"device_id": "sound", "values": {"volume": 0}, "at": AT},
]


class FaultySimulator:
    def __init__(self, fail_post=0, uncertain=False, fail_get=0, drift=False):
        self.actual = {"light": {"brightness": 70}, "sound": {"volume": 20}}
        self.posts = 0
        self.gets = 0
        self.fail_post, self.uncertain = fail_post, uncertain
        self.fail_get, self.drift = fail_get, drift

    async def request(self, method, path, **kwargs):
        if method == "GET":
            self.gets += 1
            if self.gets == self.fail_get:
                raise ServiceError("UPSTREAM_UNCERTAIN", "GET state timed out")
            if self.drift and self.posts == 1 and self.gets >= 2:
                self.actual["sound"]["volume"] = 77  # another actor
            return {"state": deepcopy(self.actual)}
        self.posts += 1
        if self.posts == self.fail_post and not self.uncertain:
            raise ServiceError("UPSTREAM_ERROR", "rejected")
        command = kwargs["body"]
        self.actual[command["device_id"]].update(command["values"])
        if self.posts == self.fail_post and self.uncertain:
            raise ServiceError("UPSTREAM_UNCERTAIN", "reply lost")
        return {}


def test_second_action_failure_reports_confirmed_partial_not_done():
    sim = FaultySimulator(fail_post=2)
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "offline"})
    with pytest.raises(ServiceError) as captured:
        asyncio.run(room.execute(COMMANDS, AT, operation_id="op-partial"))
    assert captured.value.code == "ACTION_PARTIAL"
    assert captured.value.confirmed_devices == ["light"]
    assert sim.posts == 2
    assert room.operations["op-partial"]["status"] == "partial"


def test_lost_reply_must_reconcile_without_duplicate_post():
    sim = FaultySimulator(fail_post=1, uncertain=True)
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "offline"})
    result = asyncio.run(room.execute(COMMANDS[:1], AT, operation_id="op-lost"))
    assert result["light"]["brightness"] == 0
    assert sim.posts == 1
    assert room.operations["op-lost"]["status"] == "done"
    # A double-submit of the same operation must never POST again.
    assert asyncio.run(room.execute(COMMANDS[:1], AT, operation_id="op-lost")) == result
    assert sim.posts == 1


def test_timeout_after_post_stays_uncertain_and_cannot_be_replayed():
    sim = FaultySimulator(fail_get=2)
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "offline"})
    for attempt in range(2):
        with pytest.raises(ServiceError) as captured:
            asyncio.run(room.execute(COMMANDS[:1], AT, operation_id="op-get-lost"))
        assert captured.value.code == "ACTION_UNCERTAIN"
        assert sim.posts == 1
    assert room.operations["op-get-lost"]["status"] == "uncertain"


def test_external_state_change_prevents_second_post():
    sim = FaultySimulator(drift=True)
    room = Room(SimpleNamespace(request=sim.request), {"session_id": "offline"})
    with pytest.raises(ServiceError) as captured:
        asyncio.run(room.execute(COMMANDS, AT, operation_id="op-drift"))
    assert captured.value.code in {"ACTION_CONFLICT", "ACTION_PARTIAL"}
    assert sim.posts == 1  # no duplicate / overwriting somebody else's change
