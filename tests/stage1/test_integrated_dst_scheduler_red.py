"""Independent integrated DST oracle: device timelines are real hotel instants."""
from datetime import timedelta, timezone
import pytest

from backend.core import hotel_moment
from backend.scheduler import build_scenario
from tests.helpers import dataset, prefs


@pytest.mark.parametrize("zone,check_in,wake", [
    ("Europe/Berlin", "2026-03-28T21:00:00+01:00", "2026-03-29T03:15:00+02:00"),
    ("Europe/Berlin", "2026-10-24T21:00:00+02:00", "2026-10-25T02:15:00+01:00"),
    ("America/New_York", "2026-03-07T21:00:00-05:00", "2026-03-08T03:15:00-04:00"),
    ("America/New_York", "2026-10-31T21:00:00-04:00", "2026-11-01T01:15:00-05:00"),
    ("Europe/Moscow", "2026-11-12T21:00:00+03:00", "2026-11-13T07:00:00+03:00"),
])
def test_all_scheduled_events_use_iana_offset_of_actual_event_instant(zone, check_in, wake):
    data = dataset()
    stay = data["stays"][0]
    stay.update(hotel_timezone=zone, check_in_at=check_in, target_wake_at=wake)
    user = data["users"][0]
    user["timezone"] = zone
    scheduled = build_scenario(user, stay, prefs(), data["devices"], data["sleep_rules"])
    assert scheduled
    start_utc = hotel_moment(check_in, zone).astimezone(timezone.utc)
    wake_utc = hotel_moment(wake, zone).astimezone(timezone.utc)
    for step in scheduled:
        observed = hotel_moment(step["at"], zone).astimezone(timezone.utc)
        assert start_utc <= observed <= wake_utc
    rises = sorted(
        [step for step in scheduled if step["device_id"] == "light" and
         step["values"].get("brightness") in (10, 30, 60)],
        key=lambda x: hotel_moment(x["at"], zone).astimezone(timezone.utc)
    )
    assert [x["values"]["brightness"] for x in rises] == [10, 30, 60]
    assert [(wake_utc - hotel_moment(x["at"], zone).astimezone(timezone.utc))
            for x in rises] == [timedelta(minutes=i) for i in (30, 23, 16)]


@pytest.mark.parametrize("zone,check_in,wake", [
    ("Europe/Berlin", "2026-03-29T01:50:00+01:00", "2026-03-29T03:15:00+02:00"),
    ("America/New_York", "2026-11-01T01:05:00-04:00", "2026-11-01T01:15:00-05:00"),
])
def test_dst_short_stay_curtain_fallback_is_real_instant(zone, check_in, wake):
    data = dataset()
    stay = data["stays"][0]
    stay.update(hotel_timezone=zone, check_in_at=check_in, target_wake_at=wake)
    data["users"][0]["timezone"] = zone
    steps = build_scenario(data["users"][0], stay, prefs(), data["devices"], data["sleep_rules"])
    for step in steps:
        hotel_moment(step["at"], zone)
    # If the check-in is within a real 15..30 minute window before wake,
    # an R6-compliant alternative must be planned; otherwise no fabricated action.
    arrival = hotel_moment(check_in, zone).astimezone(timezone.utc)
    end = hotel_moment(wake, zone).astimezone(timezone.utc)
    curtain = [x for x in steps if x["device_id"] == "curtains" and x["values"].get("position") == 100]
    if timedelta(minutes=15) <= end-arrival < timedelta(minutes=30):
        assert len(curtain) >= 1
        assert all(timedelta(minutes=15) <= end-hotel_moment(x["at"],zone).astimezone(timezone.utc)
                   <= timedelta(minutes=30) for x in curtain)
