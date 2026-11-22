"""Stage 2 golden, independent bedtime + R1–R8 oracle (not using scheduler bedtime())."""
from copy import deepcopy
from itertools import product

import pytest

from backend.core import moment
from backend.scheduler import build_scenario
from scripts.sleep_audit import audit
from tests.helpers import CATALOG, dataset, prefs


@pytest.mark.parametrize("home,temp,has_track,gentle", list(product(
    ["Europe/Moscow", "Europe/London"],
    ["cool", "neutral", "warm"],
    [False, True], [False, True],
)))
def test_24_golden_overnights_satisfy_independent_r1_r8_oracle(home, temp, has_track, gentle):
    d = dataset()
    stay = d["stays"][0]
    user = d["users"][0]
    user["timezone"] = home
    personal = prefs()
    personal["temperature"] = temp
    personal["tracks"] = ["track_04"] if has_track else []
    personal["alarm_mode"] = "light" if gentle else "both"
    # These two independent expected dates are manually resolved by ordinary
    # clock arithmetic, NOT calculated from backend.scheduler.bedtime.
    expected_bed = ("2026-11-12T23:00:00+03:00"
                    if home == "Europe/Moscow" else "2026-11-13T01:00:00+03:00")
    expected = {"resolved_bedtime_at": expected_bed,
                "resolved_preferences": {
                    "temperature": "normal" if temp == "neutral" else temp,
                    "favorite_track_ids": personal["tracks"],
                    "gentle_alarm": gentle}}
    steps = build_scenario(user, stay, personal, d["devices"], d["sleep_rules"])
    assert audit(stay, expected, steps, d["devices"]) == []
    assert any(step["at"] == expected_bed and step["device_id"] == "light"
               and step["values"].get("brightness") == 0 for step in steps), "R8 golden bedtime"
    assert all(moment(stay["check_in_at"]) <= moment(step["at"]) <= moment(stay["target_wake_at"])
               for step in steps)


def test_oracle_detects_unexpected_night_temperature_mutation():
    d = dataset()
    p = prefs()
    expected = {"resolved_bedtime_at": "2026-11-12T23:00:00+03:00",
                "resolved_preferences": {"temperature": "normal",
                                          "favorite_track_ids": [], "gentle_alarm": False}}
    steps = build_scenario(d["users"][0], d["stays"][0], p, d["devices"], d["sleep_rules"])
    assert audit(d["stays"][0], expected, steps, d["devices"]) == []
    broken = deepcopy(steps)
    broken.append({"at": "2026-11-13T01:00:00+03:00", "device_id": "climate",
                   "values": {"temperature_c": 26}})
    assert "R3" in audit(d["stays"][0], expected, broken, d["devices"])
