"""MR-003: bedtime candidate uses real UTC chronology on DST fold and gap."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import pytest
from backend.scheduler import bedtime, build_scenario
from backend.core import moment, hotel_moment
from tests.helpers import dataset, prefs


def setup(zone, wake, bed, home_zone=None, checkin=None):
    data = dataset()
    user, stay = data["users"][0], data["stays"][0]
    user["timezone"] = home_zone or zone
    user["weekday_bedtime"] = bed
    stay.update(hotel_timezone=zone, target_wake_at=wake,
                check_in_at=checkin or "2026-10-31T18:00:00-04:00")
    return data, user, stay


def utc(value):
    return value.astimezone(timezone.utc)


def test_ny_second_fold_wakeup_allows_first_fold_bedtime():
    data, user, stay = setup("America/New_York", "2026-11-01T01:30:00-05:00", "01:45")
    result = bedtime(user, stay)
    assert utc(result) == datetime(2026, 11, 1, 5, 45, tzinfo=timezone.utc)
    assert utc(result) < utc(moment(stay["target_wake_at"]))
    steps = build_scenario(user, stay, prefs(), data["devices"], data["sleep_rules"])
    assert any(step["device_id"] == "light" and step["values"].get("brightness") == 0
               and moment(step["at"]).astimezone(timezone.utc) == utc(result)
               for step in steps)
    assert all(hotel_moment(step["at"], stay["hotel_timezone"]) for step in steps)
    assert [utc(moment(step["at"])) for step in steps] == sorted(utc(moment(step["at"])) for step in steps)


def test_ny_fold_bedtime_policy_chooses_earliest_instant():
    data, user, stay = setup("America/New_York", "2026-11-01T03:30:00-05:00", "01:45")
    assert utc(bedtime(user, stay)) == datetime(2026, 11, 1, 5, 45, tzinfo=timezone.utc)


def test_spring_gap_bedtime_moves_forward_to_first_real_local_instant():
    data, user, stay = setup("America/New_York", "2026-03-08T05:30:00-04:00",
                             "02:30", checkin="2026-03-07T18:00:00-05:00")
    result = bedtime(user, stay)
    assert result.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M") == "03:30"
    assert utc(result) == datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc)
    steps = build_scenario(user, stay, prefs(), data["devices"], data["sleep_rules"])
    assert all(hotel_moment(s["at"], "America/New_York") for s in steps)
    assert [utc(moment(s["at"])) for s in steps] == sorted(utc(moment(s["at"])) for s in steps)


def test_distinct_home_and_hotel_zones_keep_r8_real_hour_adjustment():
    data, user, stay = setup("Europe/Berlin", "2026-11-13T07:00:00+01:00",
                             "23:00", home_zone="America/New_York",
                             checkin="2026-11-12T14:00:00+01:00")
    result = bedtime(user, stay)
    assert utc(result) < utc(moment(stay["target_wake_at"]))
    steps = build_scenario(user, stay, prefs(), data["devices"], data["sleep_rules"])
    assert all(hotel_moment(step["at"], "Europe/Berlin") for step in steps)
    assert [utc(moment(s["at"])) for s in steps] == sorted(utc(moment(s["at"])) for s in steps)


def test_regular_moscow_night_and_r6_always_chronological():
    data, user, stay = setup("Europe/Moscow", "2026-11-13T07:00:00+03:00",
                            "23:00", checkin="2026-11-12T18:00:00+03:00")
    assert utc(bedtime(user, stay)) < utc(moment(stay["target_wake_at"]))
    steps = build_scenario(user, stay, prefs(), data["devices"], data["sleep_rules"])
    assert [utc(moment(s["at"])) for s in steps] == sorted(utc(moment(s["at"])) for s in steps)
    assert len([s for s in steps if s["device_id"] == "light" and s["values"].get("brightness") in (10,30,60)]) == 3


@pytest.mark.parametrize("hotel,home,wake,expected", [
    ("Europe/Berlin", "America/New_York", "2026-11-13T07:00:00+01:00",
     datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc)),  # R8 -1 real hour
    ("America/New_York", "Asia/Tokyo", "2026-11-13T07:00:00-05:00",
     datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc)),  # R8 +1 real hour
])
def test_r8_shift_is_one_real_utc_hour_not_an_ambiguous_wall_hour(hotel, home, wake, expected):
    data, user, stay = setup(hotel, wake, "23:00", home_zone=home)
    actual = bedtime(user, stay)
    assert utc(actual) == expected
    steps = build_scenario(user, stay, prefs(), data["devices"], data["sleep_rules"])
    assert [utc(moment(s["at"])) for s in steps] == sorted(utc(moment(s["at"])) for s in steps)
    assert all(hotel_moment(s["at"], hotel) for s in steps)
