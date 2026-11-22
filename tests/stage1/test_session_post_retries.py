"""Stage 1 S-009: fault injected upstream session creation, no real requests."""
import asyncio
from types import SimpleNamespace
import pytest
from backend.core import ServiceError
from backend.room import Room


def test_uncertain_session_creation_must_not_retry_unsafe_post():
    posts = []
    async def request(method, path, **kwargs):
        assert method == "POST" and path == "/room/session"
        posts.append(kwargs)
        if kwargs.get("retry"):
            # Emulate an upstream client which repeats a POST after a lost reply.
            posts.append(kwargs)
            return {"session_id": "duplicate", "initial_state": {}}
        raise ServiceError("UPSTREAM_UNCERTAIN", "POST completed but its reply was lost")
    async def check():
        with pytest.raises(ServiceError) as exc:
            await Room.create(SimpleNamespace(request=request), "stay_test", "stay")
        assert exc.value.code == "UPSTREAM_UNCERTAIN"
    asyncio.run(check())
    assert len(posts) == 1, "A timeout must not create a second upstream session"
    assert posts[0].get("retry") is not True
