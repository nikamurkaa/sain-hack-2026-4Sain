"""Independent property checks for synthetic stays, time zones and DST.

Not an official validator and not an NLU benchmark.
"""
from datetime import datetime, timedelta, timezone
from itertools import product
from zoneinfo import ZoneInfo

import pytest

from backend.core import moment, check_values
from backend.scheduler import build_scenario
from tests.helpers import CATALOG, dataset, prefs


@pytest.mark.parametrize("hotel,home,temperature,track", list(product(
    ["Europe/Berlin", "Europe/London", "Asia/Tokyo", "America/New_York"],
    ["Europe/Moscow", "Europe/London"],
    ["cool", "warm"],
    [False, True],
)))
def test_32_synthetic_guest_scenarios_are_bounded_and_valid(hotel, home, temperature, track):
    d = dataset()
    user = d["users"][0]
    user["timezone"] = home
    user["chronotype"] = "evening" if temperature == "cool" else "morning"
    stay = d["stays"][0]
    checkin = datetime(2026, 11, 12, 20, tzinfo=ZoneInfo("Europe/Moscow"))
    stay["hotel_timezone"] = hotel
    stay["check_in_at"] = checkin.astimezone(ZoneInfo(hotel)).isoformat(timespec="seconds")
    stay["target_wake_at"] = (checkin.astimezone(timezone.utc) + timedelta(hours=11)).astimezone(
        ZoneInfo(hotel)).isoformat(timespec="seconds")
    personal = prefs()
    personal["temperature"] = temperature
    personal["tracks"] = ["track_04"] if track else []
    steps = build_scenario(user, stay, personal, d["devices"], d["sleep_rules"])
    assert steps
    start = moment(stay["check_in_at"])
    wake = moment(stay["target_wake_at"])
    assert all(start <= moment(step["at"]) <= wake for step in steps)
    assert [moment(step["at"]) for step in steps] == sorted(moment(step["at"]) for step in steps)
    for step in steps:
        assert moment(step["at"]).astimezone(ZoneInfo(hotel)).utcoffset() == moment(step["at"]).utcoffset()
        check_values(d["devices"], step["device_id"], step["values"])


@pytest.mark.parametrize("checkin,wake", [
    ("2026-03-28T21:30:00+01:00", "2026-03-29T07:00:00+02:00"),
    ("2026-10-24T21:30:00+02:00", "2026-10-25T07:00:00+01:00"),
])
def test_spring_and_fall_berlin_dst_schedules_are_real_instants(checkin, wake):
    d = dataset()
    d["users"][0]["timezone"] = "Europe/Berlin"
    d["stays"][0].update(hotel_timezone="Europe/Berlin",
                          check_in_at=checkin, target_wake_at=wake)
    steps = build_scenario(d["users"][0], d["stays"][0], prefs(),
                           d["devices"], d["sleep_rules"])
    assert steps
    for step in steps:
        timestamp = moment(step["at"])
        local = timestamp.astimezone(ZoneInfo("Europe/Berlin"))
        assert timestamp.replace(tzinfo=None) == local.replace(tzinfo=None)
        assert timestamp.utcoffset() == local.utcoffset()
        assert moment(checkin) <= timestamp <= moment(wake)
