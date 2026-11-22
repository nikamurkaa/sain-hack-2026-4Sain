"""Independent Stage 2 checks for source isolation, truthful display and cache freshness."""
import asyncio
from copy import deepcopy
from backend.explanations import preparation_explanations
from backend.preferences import PreferenceResolver
from backend.scheduler import build_scenario
from tests.helpers import AT, dataset, prefs


def test_explain_six_devices_and_no_private_source_data():
    data = dataset()
    p = prefs()
    p.update(temperature="cool", tracks=["track_04"], alarm_mode="light")
    p["sources"] = {"temperature": {"source": "chat:secret", "quote": "personal message"}}
    steps = build_scenario(data["users"][0], data["stays"][0], p, data["devices"], data["sleep_rules"])
    explanations = preparation_explanations(data["users"][0], data["stays"][0], p, steps)
    assert {entry["device_id"] for entry in explanations} == {
        "light", "curtains", "climate", "sound", "alarm", "dnd"}
    assert all(entry["status"] == "planned" for entry in explanations)
    assert any("17.5" in entry["reason"] and entry["source"] == "history" for entry in explanations)
    assert all("secret" not in entry["reason"] and "personal message" not in entry["reason"]
               for entry in explanations)


def test_r6_impossible_short_stay_is_explicit_warning():
    data = dataset()
    data["stays"][0]["check_in_at"] = "2026-11-13T06:52:00+03:00"
    p = prefs()
    steps = build_scenario(data["users"][0], data["stays"][0], p, data["devices"], data["sleep_rules"])
    explanations = preparation_explanations(data["users"][0], data["stays"][0], p, steps)
    assert any(entry["status"] == "warning" and entry["reason"].startswith("R6:")
               for entry in explanations)


def test_updated_note_and_profile_invalidate_preference_cache():
    data = dataset()
    data["events"] = [{"event_id": "unchanged-id", "user_id": "guest_test", "source": "app",
                       "started_at": AT, "payload": {"text": "Люблю прохладу."}}]
    class Model:
        calls = 0
        async def json(self, instruction, payload, output_tokens=3500):
            self.calls += 1
            e = payload["history"][0]
            return {"facts": [{"key": "temperature", "value":
                               "cool" if "прохладу" in e["text"] else "warm",
                               "source_id": e["id"], "quote": e["text"]}]}
    async def check():
        model = Model(); resolver = PreferenceResolver(data, model)
        first = await resolver.resolve("guest_test", AT, "2026-11-11")
        data["events"][0]["payload"]["text"] = "Люблю тепло."
        second = await resolver.resolve("guest_test", AT, "2026-11-11")
        assert first["temperature"] == "cool" and second["temperature"] == "warm"
        assert model.calls == 2
        data["users"][0]["chronotype"] = "evening"
        await resolver.resolve("guest_test", AT, "2026-11-11")
        assert model.calls == 3
    asyncio.run(check())


def test_other_guest_notes_never_reach_resolver():
    data = dataset()
    guest = deepcopy(data["users"][0]); guest["user_id"] = "second"
    data["users"].append(guest)
    for uid, text in [("guest_test", "Люблю прохладу."), ("second", "Люблю тепло.")]:
        data["events"].append({"event_id": "shared", "user_id": uid, "source": "app",
                               "started_at": AT, "payload": {"text": text}})
    class Model:
        async def json(self, instruction, payload, output_tokens=3500):
            assert len(payload["history"]) == 1
            e = payload["history"][0]
            return {"facts": [{"key": "temperature",
                               "value": "cool" if "прохладу" in e["text"] else "warm",
                               "source_id": e["id"], "quote": e["text"]}]}
    async def check():
        r = PreferenceResolver(data, Model())
        assert (await r.resolve("guest_test", AT, "2026-11-11"))["temperature"] == "cool"
        assert (await r.resolve("second", AT, "2026-11-11"))["temperature"] == "warm"
    asyncio.run(check())
