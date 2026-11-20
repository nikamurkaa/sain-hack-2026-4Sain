"""Contract-driven score-hardening regressions. All I/O is mocked."""
import asyncio
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest

from backend.commands import Refusal, plan_commands
from backend.core import ServiceError, default_state, moment
from backend.intents import Intent
from backend.preferences import parse_facts
from backend.room import Room
from backend.runner import open_solution
from backend.scheduler import bedtime, build_scenario
from tests.helpers import AT, CATALOG, FakeModel, dataset, prefs
from tests.simulator import Simulator


def test_A01_done_requires_unchanged_fields():
    initial = default_state(CATALOG["devices"])
    initial["light"].update(brightness=70, color_temperature_k=3300)
    modified = deepcopy(initial)
    modified["light"].update(brightness=0, color_temperature_k=6500)
    applied = False
    async def fake_request(method, path, **kwargs):
        nonlocal applied
        if method == "POST":
            applied = True
            return {}
        return {"state": deepcopy(modified if applied else initial)}
    room = Room(SimpleNamespace(request=fake_request), {"session_id":"isolated", "initial_state": initial})
    with pytest.raises(ServiceError, match="подтверждены"):
        asyncio.run(room.execute([{"device_id":"light", "values":{"brightness":0}, "at":AT}], AT))


@pytest.mark.parametrize("name,value", [
    ("cooler",25), ("warmer",21), ("dimmer",90), ("brighter",50), ("quieter",80),
])
def test_A02_relative_direction_cannot_reverse(name, value):
    state = default_state(CATALOG["devices"])
    with pytest.raises(Refusal):
        plan_commands(Intent(intent=name, value=value), state, prefs(), AT, CATALOG["devices"], CATALOG["tracks"])


def test_A03_explicit_tomorrow_even_if_today_time_not_past():
    current = "2026-11-12T06:00:00+03:00"
    action = plan_commands(Intent(intent="alarm_set", time="09:00", day_offset=1),
                           default_state(CATALOG["devices"]), prefs(), current, CATALOG["devices"], CATALOG["tracks"])
    assert action[0]["values"]["at"] == "2026-11-13T09:00:00+03:00"


def test_A03_relative_alarm_after_two_hours():
    current = "2026-11-12T06:00:00+03:00"
    action = plan_commands(Intent(intent="alarm_set", after_minutes=120),
                           default_state(CATALOG["devices"]), prefs(), current, CATALOG["devices"], CATALOG["tracks"])
    assert action[0]["values"]["at"] == "2026-11-12T08:00:00+03:00"


def test_A04_favorite_sound_at_bedtime_not_five_minutes_later():
    data = dataset()
    p = prefs()
    p.update(tracks=["track_04"], timer=30, volume=15)
    steps = build_scenario(data["users"][0], data["stays"][0], p, data["devices"], data["sleep_rules"])
    bed = bedtime(data["users"][0], data["stays"][0])
    starts = [s for s in steps if s["device_id"] == "sound" and s["values"].get("volume",0)>0]
    assert len(starts) == 1
    assert moment(starts[0]["at"]) == bed
    stops = [s for s in steps if s["device_id"] == "sound" and s["values"].get("volume") == 0]
    assert moment(stops[0]["at"]) == bed + timedelta(minutes=30)


def test_A05_three_dawn_steps_within_15_to_30_minutes():
    data = dataset()
    steps = build_scenario(data["users"][0], data["stays"][0], prefs(), data["devices"], data["sleep_rules"])
    wake = moment(data["stays"][0]["target_wake_at"])
    rises = [(moment(s["at"]),s["values"]["brightness"]) for s in steps
             if s["device_id"]=="light" and s["values"].get("brightness",0)>0
             and wake-timedelta(minutes=30) <= moment(s["at"]) <= wake-timedelta(minutes=15)]
    assert len(rises)>=3
    assert [brightness for _,brightness in rises] == sorted({brightness for _,brightness in rises})


def test_A09_one_invalid_fact_does_not_destroy_supported_fact():
    history = [{"id":"chat:1", "at":AT, "text":"Мне комфортно в прохладе"},
               {"id":"chat:2", "at":AT, "text":"Попробуй неподдерживаемое поле"}]
    raw = {"facts":[{"key":"temperature","value":"cool","source_id":"chat:1","quote":"Мне комфортно в прохладе"},
                    {"key":"home.light.unknown","value":999,"source_id":"chat:2","quote":"Попробуй неподдерживаемое поле"}]}
    facts = parse_facts(raw,history,CATALOG["devices"],CATALOG["tracks"])
    assert set(facts)=={"temperature"} and facts["temperature"]["value"]=="cool"


def test_A10_one_bad_stay_does_not_abort_all_other_records():
    async def check():
        sim = Simulator()
        async with httpx.AsyncClient(transport=httpx.MockTransport(sim),trust_env=False) as http:
            solution = await open_solution("offline","case2-dev-v1",http,FakeModel())
            async def broken_prepare(stay):
                raise ValueError("bad individual stay")
            solution.prepare = broken_prepare
            answer = await solution.run()
            assert answer["stays"]==[]
            assert len(answer["requests"])==1
    asyncio.run(check())
