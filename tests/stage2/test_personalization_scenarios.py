"""Stage 2 personalization evidence → planned and actual simulator actions.

The fixed extractor is a test double. It validates precedence, provenance,
content edits and isolation, NOT real-language semantic extraction.
"""
import asyncio
from copy import deepcopy
from datetime import timedelta
import json

import httpx
import pytest

from backend.commands import Refusal, plan_commands
from backend.core import default_state, moment
from backend.intents import Intent
from backend.preferences import PreferenceResolver
from backend.runner import open_solution
from backend.scheduler import build_scenario
from tests.helpers import AT, CATALOG, dataset, prefs
from tests.simulator import Simulator

NIGHT = "2026-11-12T23:05:00+03:00"
AFTER_ARRIVAL = "2026-11-12T20:45:00+03:00"


def note(data, event_id, text, at="2026-11-11T18:00:00+03:00", uid="guest_test", source="hotel"):
    data["events"].append({"event_id": event_id, "source": source, "user_id": uid,
                           "started_at": at, "ended_at": None, "type": "note", "payload": {"text": text}})


class EvidenceModel:
    def __init__(self, replacements=None):
        self.replacements = replacements or {}
        self.calls = []
    async def json(self, instruction, payload, output_tokens=3500):
        if "utterances" in payload:
            phrase = payload["utterances"][-1]
            return {"intent": {"Как дома":"like_home", "Как вчера":"like_yesterday",
                               "Я ложусь":"going_to_bed"}.get(phrase, "out_of_scope")}
        entries = payload.get("hotel_notes", []) + payload.get("history", [])
        self.calls.append([e["id"] for e in entries])
        facts = []
        for e in entries:
            text = e["text"]
            mapping = {
                "Раньше в отеле было тепло": ("temperature", "warm"),
                "Теперь в отеле люблю прохладу": ("temperature", "cool"),
                "В гостиницах по-прежнему люблю тепло": ("temperature", "warm"),
                "Дома выставляю 18 градусов": ("home.climate.temperature_c", 18),
                "Вчера яркость была 33 процента": ("yesterday.light.brightness", 33),
                "Резкий звук будильника мне не нравится": ("alarm_mode", "light"),
            }
            if text in mapping:
                key, value = mapping[text]
                facts.append({"key":key, "value":value, "source_id":e["id"], "quote":text})
        return {"facts": facts}


def night_state(steps):
    out = default_state(CATALOG["devices"])
    for step in sorted(steps, key=lambda row: moment(row["at"])):
        if moment(step["at"]) <= moment(NIGHT):
            out[step["device_id"]].update(step["values"])
    return out


@pytest.mark.parametrize("profile,old,new,want,source", [
    ("cool", "Раньше в отеле было тепло", "В гостиницах по-прежнему люблю тепло", 17.5, "profile"),
    ("warm", "Раньше в отеле было тепло", "Теперь в отеле люблю прохладу", 21.5, "profile"),
    (None, "Раньше в отеле было тепло", "Теперь в отеле люблю прохладу", 17.5, "history"),
    (None, "Теперь в отеле люблю прохладу", "В гостиницах по-прежнему люблю тепло", 21.5, "history"),
])
def test_conflicting_profile_history_and_recent_hotel_behavior_in_scenario(profile, old, new, want, source):
    data = dataset()
    data["users"][0]["sleep_preferences"] = {
        "temperature": profile, "favorite_track_ids": None,
        "light_sensitive": None, "dislikes": []}
    note(data, "old", old, at="2026-11-09T19:00:00+03:00")
    note(data, "new", new, at="2026-11-11T18:00:00+03:00")
    async def check():
        resolved = await PreferenceResolver(data, EvidenceModel()).resolve("guest_test", AT, "2026-11-11")
        steps = build_scenario(data["users"][0], data["stays"][0], resolved,
                               data["devices"], data["sleep_rules"])
        assert night_state(steps)["climate"]["temperature_c"] == want
        assert resolved["sources"]["temperature"]["source"] == source if source == "profile" else (
               resolved["sources"]["temperature"]["source"].startswith("event:"))
    asyncio.run(check())


def test_one_time_adjustment_not_promoted_to_permanent_hotel_preference():
    data = dataset()
    note(data, "old", "Раньше в отеле было тепло", at="2026-11-09T19:00:00+03:00")
    note(data, "temporary", "Разово только на этот вечер поставь 16 градусов",
         at="2026-11-11T18:00:00+03:00")
    async def check():
        resolved = await PreferenceResolver(data, EvidenceModel()).resolve("guest_test", AT, "2026-11-11")
        steps = build_scenario(data["users"][0], data["stays"][0], resolved,
                               data["devices"], data["sleep_rules"])
        assert resolved["temperature"] == "warm"
        assert night_state(steps)["climate"]["temperature_c"] == 21.5
        assert all("temporary" not in json.dumps(f, ensure_ascii=False)
                   for f in resolved["sources"].values())
    asyncio.run(check())


def test_disliked_alarm_sound_changes_planned_mode_without_invented_details():
    data = dataset()
    data["users"][0]["sleep_preferences"] = {
        "temperature": None, "favorite_track_ids": None,
        "light_sensitive": None, "dislikes": ["Резкий звук будильника мне не нравится"]}
    async def check():
        resolved = await PreferenceResolver(data, EvidenceModel()).resolve("guest_test", AT, "2026-11-11")
        steps = build_scenario(data["users"][0], data["stays"][0], resolved,
                               data["devices"], data["sleep_rules"])
        assert resolved["alarm_mode"] == "light"
        assert night_state(steps)["alarm"]["mode"] == "light"
        assert resolved["sources"]["alarm_mode"]["source"] == "profile:dislikes"
    asyncio.run(check())


def test_empty_evidence_defaults_are_explicit_and_home_yesterday_refuse_without_posts():
    data = dataset()
    async def check():
        resolved = await PreferenceResolver(data, EvidenceModel()).resolve("guest_test", AT, "2026-11-11")
        assert set(resolved["defaults"]) == {"temperature","tracks","volume","timer","alarm_mode"}
        assert resolved["home"] == resolved["yesterday"] == {}
        current = default_state(CATALOG["devices"])
        before = deepcopy(current)
        for name in ("like_home", "like_yesterday"):
            with pytest.raises(Refusal):
                plan_commands(Intent(intent=name), current, resolved, AT,
                              data["devices"], data["tracks"])
            assert current == before
    asyncio.run(check())


def test_like_home_and_yesterday_act_on_actual_simulator_without_cross_contamination():
    sim = Simulator()
    note(sim.data, "home", "Дома выставляю 18 градусов", source="app")
    note(sim.data, "yesterday", "Вчера яркость была 33 процента", source="app")
    async def check():
        model = EvidenceModel()
        async with httpx.AsyncClient(transport=httpx.MockTransport(sim), trust_env=False) as http:
            sol = await open_solution("offline-eval", "case2-dev-v1", http, model)
            room, resolved, _ = await sol.prepare(sim.data["stays"][0])
            before = await room.state(AFTER_ARRIVAL)
            initial_posts = sim.actions
            reply, returned = await sol.message(
                room, "guest_test", ["Как дома"], AFTER_ARRIVAL)
            assert reply["response_class"] == "done"
            expected = deepcopy(before)
            expected["climate"]["temperature_c"] = 18
            assert returned == expected
            assert await room.state(AFTER_ARRIVAL) == expected
            assert sim.actions == initial_posts + 1
            reply, actual = await sol.message(room, "guest_test", ["Как вчера"], AFTER_ARRIVAL)
            expected["light"]["brightness"] = 33
            assert reply["response_class"] == "done"
            assert actual == expected and await room.state(AFTER_ARRIVAL) == expected
            assert sim.actions == initial_posts + 2
            assert resolved["home"]["climate"]["temperature_c"] == 18
            assert resolved["yesterday"]["light"]["brightness"] == 33
    asyncio.run(check())


def test_hotel_stay_preference_change_under_same_event_id_updates_next_scenario():
    data = dataset()
    note(data, "same-id", "Раньше в отеле было тепло")
    model = EvidenceModel()
    async def check():
        resolver = PreferenceResolver(data, model)
        first = await resolver.resolve("guest_test", AT, "2026-11-11")
        temp1 = night_state(build_scenario(data["users"][0], data["stays"][0], first,
                            data["devices"], data["sleep_rules"]))["climate"]["temperature_c"]
        data["events"][0]["payload"]["text"] = "Теперь в отеле люблю прохладу"
        second = await resolver.resolve("guest_test", AT, "2026-11-11")
        temp2 = night_state(build_scenario(data["users"][0], data["stays"][0], second,
                            data["devices"], data["sleep_rules"]))["climate"]["temperature_c"]
        assert (temp1,temp2) == (21.5, 17.5)
        assert len(model.calls) == 2
    asyncio.run(check())


def test_two_guests_same_event_id_and_time_but_different_preferences_never_mix():
    data = dataset()
    other = deepcopy(data["users"][0]); other["user_id"] = "guest_B"
    data["users"].append(other)
    note(data, "same-id", "Теперь в отеле люблю прохладу", uid="guest_test")
    note(data, "same-id", "В гостиницах по-прежнему люблю тепло", uid="guest_B")
    async def check():
        model = EvidenceModel()
        resolver = PreferenceResolver(data, model)
        a,b = await asyncio.gather(
            resolver.resolve("guest_test", AT, "2026-11-11"),
            resolver.resolve("guest_B", AT, "2026-11-11"))
        assert a["temperature"] == "cool" and b["temperature"] == "warm"
        assert len(model.calls) == 2 and all(len(row) == 1 for row in model.calls)
    asyncio.run(check())
