"""Stage 2 full-stack gate: REAL local FastAPI and MockSimulator, no organizer API.

These expectation tables are independent of plan_commands and of its delta
arithmetic. A scripted model is intentionally used only for the explicit 19
catalogue labels; this is NOT NLU generalization or AI-model accuracy.
"""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from scripts.rehearse_client import build_rehearsal
from tests.helpers import WAKE
from tests.offline_cases import CASES


T = "2026-11-12T20:45:00+03:00"

# Expected changed fields are handwritten, NOT computed with the command planner.
# In this rehearsal, no hotel/home preference evidence is supplied; the two
# history-dependent intentions must safely refuse without changing anything.
EXPECT = [
    {"light": {"brightness": 90}},
    {"light": {"brightness": 50}},
    {"climate": {"temperature_c": 24}},
    {"climate": {"temperature_c": 22}},
    {"light": {"brightness": 0}, "sound": {"volume": 0}},
    {"sound": {"track_id": "track_04", "volume": 30}},
    {"sound": {"volume": 10}},
    {"curtains": {"position": 0}},
    {"alarm": {"at": "2026-11-13T06:30:00+03:00"}},
    {"alarm": {"at": "2026-11-13T07:30:00+03:00"}},
    {"alarm": {"at": None}},
    {"light": {"brightness": 0}, "curtains": {"position": 0},
     "dnd": {"enabled": True}, "climate": {"temperature_c": 19.5},
     "sound": {"volume": 0}},
    {"alarm": {"at": None}, "dnd": {"enabled": False},
     "light": {"brightness": 70, "color_temperature_k": 4000}},
    None,
    {"dnd": {"enabled": True}},
    None,
    None, None, None,
]
assert len(EXPECT) == len(CASES) == 19


def local_guest(api, stay_id="stay_test"):
    result = api.post("/api/v1/sessions", headers={"Authorization": "Bearer offline-team"},
                      json={"source": "dev", "stay_id": stay_id})
    assert result.status_code == 201, result.text
    token = result.json()["session_token"]
    return {"Authorization": "Bearer " + token}


def state(api, auth):
    result = api.get("/api/v1/state", headers=auth, params={"at": T})
    assert result.status_code == 200, result.text
    return result.json()["state"]


def send(api, auth, phrase, key):
    return api.post("/api/v1/messages",
                    headers={**auth, "Idempotency-Key": key},
                    json={"at": T, "text": phrase})


@pytest.mark.parametrize("i", range(19), ids=[x[1]["intent"] for x in CASES])
def test_19_families_exact_all_six_device_states_and_response_classes(i):
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        auth = local_guest(api)
        simulator = wrapper.state.rehearsal_simulator
        before = state(api, auth)
        assert set(before) == {"light", "climate", "curtains", "sound", "alarm", "dnd"}
        assert before["alarm"]["at"] == WAKE
        reference = deepcopy(before)
        delta = EXPECT[i]
        if delta:
            for device, fields in delta.items():
                reference[device].update(fields)
        posts_before = simulator.actions
        response = send(api, auth, CASES[i][0], "stage2-full-state-" + str(i).zfill(3))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["reply"]["response_class"] == ("done" if delta is not None else "refused")
        assert body["state"] == reference, ("response state", i, CASES[i][0])
        assert state(api, auth) == reference, ("actual simulator state", i, CASES[i][0])
        if delta is None:
            assert simulator.actions == posts_before, "A refusal may not POST to simulator"
        else:
            assert simulator.actions == posts_before + len(delta), "One POST per affected system"
        assert len(reference) == 6
        assert api.delete("/api/v1/session", headers=auth).status_code == 204


@pytest.mark.parametrize("device,field,limits", [
    ("light", "brightness", (0, 100)),
    ("light", "color_temperature_k", (2200, 6500)),
    ("climate", "temperature_c", (16, 26)),
    ("curtains", "position", (0, 100)),
    ("sound", "volume", (0, 100)),
    ("alarm", "window_minutes", (0, 30)),
])
def test_real_api_device_field_boundaries_preserve_unrelated_state(device, field, limits):
    wrapper = build_rehearsal()
    with TestClient(wrapper) as api:
        auth = local_guest(api)
        for index, value in enumerate(limits):
            before = state(api, auth)
            expected = deepcopy(before)
            expected[device][field] = value
            response = api.post("/api/v1/devices", headers={**auth,
                            "Idempotency-Key": f"stage2-device-{device}-{field}-{index}"},
                            json={"device_id": device, "at": T, "values": {field: value}})
            assert response.status_code == 200, response.text
            assert response.json()["reply"]["response_class"] == "done"
            assert response.json()["state"] == expected
            assert state(api, auth) == expected


def test_real_api_sequence_relative_context_sleep_override_and_all_off():
    wrapper = build_rehearsal()
    with TestClient(wrapper) as api:
        auth = local_guest(api)
        before = state(api, auth)
        expected = deepcopy(before)
        for index, (phrase, changes) in enumerate([
            ("Душно", {"climate": {"temperature_c": 22}}),
            ("Ещё немного", {"climate": {"temperature_c": 21}}),
            ("Я ложусь", {"light": {"brightness": 0}, "curtains": {"position": 0},
                          "climate": {"temperature_c": 19.5}, "sound": {"volume": 0},
                          "dnd": {"enabled": True}}),
            ("Сделай потеплее", {"climate": {"temperature_c": 20.5}}),
            ("Выключи всё", {"light": {"brightness": 0}, "sound": {"volume": 0}}),
        ]):
            for device, values in changes.items():
                expected[device].update(values)
            reply = send(api, auth, phrase, f"stage2-sequence-{index:03}")
            assert reply.status_code == 200, reply.text
            assert reply.json()["reply"]["response_class"] == "done"
            assert reply.json()["state"] == expected
            assert state(api, auth) == expected
        assert expected["climate"]["temperature_c"] == 20.5
        assert expected["dnd"]["enabled"] is True


def test_true_two_guest_concurrency_isolation_and_prepared_preferences():
    wrapper = build_rehearsal()
    with TestClient(wrapper, raise_server_exceptions=False) as api:
        sim = wrapper.state.rehearsal_simulator
        other = deepcopy(sim.data["users"][0])
        other["user_id"] = "different-guest"
        other["sleep_preferences"] = {
            "temperature": "warm", "favorite_track_ids": [],
            "light_sensitive": None, "dislikes": []}
        sim.data["users"][0]["sleep_preferences"] = {
            "temperature": "cool", "favorite_track_ids": [],
            "light_sensitive": None, "dislikes": []}
        sim.data["users"].append(other)
        stay = deepcopy(sim.data["stays"][0])
        stay.update(record_id="stay_different_guest", user_id="different-guest")
        sim.data["stays"].append(stay)
        first, second = local_guest(api), local_guest(api, "stay_different_guest")
        view1 = api.get("/api/v1/prepared", headers=first)
        view2 = api.get("/api/v1/prepared", headers=second)
        assert view1.status_code == view2.status_code == 200
        assert view1.json()["guest"]["user_id"] != view2.json()["guest"]["user_id"]
        assert view1.json()["guest"]["preferences"]["temperature"] == "cool"
        assert view2.json()["guest"]["preferences"]["temperature"] == "warm"
        assert "17.5" in str(view1.json()["explanations"])
        assert "21.5" in str(view2.json()["explanations"])
        initial1, initial2 = state(api, first), state(api, second)
        assert initial1 == initial2
        posts_before = sim.actions
        def apply(item):
            auth, value, key = item
            return api.post("/api/v1/devices", headers={**auth, "Idempotency-Key": key},
                            json={"at": T, "device_id": "light", "values": {"brightness": value}})
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(apply, [
                (first, 0, "stage2-parallel-guest-a"),
                (second, 100, "stage2-parallel-guest-b")]))
        assert all(response.status_code == 200 for response in responses), [r.text for r in responses]
        room1, room2 = state(api, first), state(api, second)
        expected1, expected2 = deepcopy(initial1), deepcopy(initial2)
        expected1["light"]["brightness"] = 0
        expected2["light"]["brightness"] = 100
        assert room1 == expected1 and room2 == expected2
        assert sim.actions == posts_before + 2
        assert view1.json()["guest"]["user_id"] == "guest_test"
        assert view2.json()["guest"]["user_id"] == "different-guest"
