"""Stage 1 S-003: independent official R6 boundary oracle (offline)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest

from backend.scheduler import build_scenario
from backend.core import moment, check_values
from tests.helpers import dataset, prefs


@pytest.mark.parametrize("minutes_before_wake", range(32))
def test_r6_uses_legal_light_or_curtains_or_marks_impossible(minutes_before_wake):
    data = dataset()
    stay = data["stays"][0]
    wake = moment(stay["target_wake_at"])
    start = wake - timedelta(minutes=minutes_before_wake)
    stay["check_in_at"] = start.isoformat()
    steps = build_scenario(data["users"][0], stay, prefs(), data["devices"], data["sleep_rules"])
    for step in steps:
        assert start <= moment(step["at"]) <= wake
        check_values(data["devices"], step["device_id"], step["values"])
    rises = [s for s in steps if s["device_id"] == "light"
             and s["values"].get("brightness", 0) > 0 and
             timedelta(minutes=15) <= wake - moment(s["at"]) <= timedelta(minutes=30)]
    curtains = [s for s in steps if s["device_id"] == "curtains"
                and s["values"].get("position", 0) >= 50 and
                timedelta(minutes=15) <= wake - moment(s["at"]) <= timedelta(minutes=30)]
    if minutes_before_wake >= 15:
        assert len({s["at"] for s in rises}) >= 3 or curtains, (
            "Official R6: three rises in 15–30m window OR open curtains"
        )
    else:
        # No instant within the required window is available after check-in.
        assert not rises and not curtains


@pytest.mark.parametrize("zone,wake_iso", [
    ("Europe/Moscow", "2026-11-13T07:00:00+03:00"),
    ("Europe/Berlin", "2026-11-13T00:10:00+01:00"),
    ("America/New_York", "2026-11-13T07:00:00-05:00"),
])
def test_short_stay_across_zones_and_midnight(zone, wake_iso):
    data = dataset()
    stay = data["stays"][0]
    wake = moment(wake_iso)
    start = wake - timedelta(minutes=25)
    stay.update(check_in_at=start.isoformat(), target_wake_at=wake_iso, hotel_timezone=zone)
    data["users"][0]["timezone"] = zone
    steps = build_scenario(data["users"][0], stay, prefs(), data["devices"], data["sleep_rules"])
    assert any(s["device_id"] == "curtains" and s["values"].get("position", 0) >= 50
               and timedelta(minutes=15) <= wake - moment(s["at"]) <= timedelta(minutes=30)
               for s in steps)
    assert all(start <= moment(s["at"]) <= wake for s in steps)
