"""Stage 1 S-004: backend rejects offset/wall-date inconsistencies for IANA hotel zone."""
from datetime import timedelta
import pytest
from backend.core import hotel_moment


@pytest.mark.parametrize("stamp,zone", [
    ("2026-03-29T03:30:00+02:00", "Europe/Berlin"),
    ("2026-10-25T02:30:00+02:00", "Europe/Berlin"),
    ("2026-10-25T02:30:00+01:00", "Europe/Berlin"),
    ("2026-03-08T03:30:00-04:00", "America/New_York"),
    ("2026-11-01T01:30:00-04:00", "America/New_York"),
    ("2026-11-01T01:30:00-05:00", "America/New_York"),
    ("2026-11-13T00:01:00+03:00", "Europe/Moscow"),
])
def test_supported_instant_has_exact_local_fields_and_offset(stamp, zone):
    assert hotel_moment(stamp, zone).isoformat(timespec="seconds") == stamp


@pytest.mark.parametrize("stamp,zone", [
    ("2026-03-29T02:30:00+01:00", "Europe/Berlin"),  # nonexistent wall clock
    ("2026-03-29T02:30:00+02:00", "Europe/Berlin"),
    ("2026-10-25T02:30:00+03:00", "Europe/Berlin"),
    ("2026-11-01T01:30:00-06:00", "America/New_York"),
    ("2026-03-29T07:00:00+02:00", "Europe/Moscow"),
])
def test_rejects_stale_offset_or_nonexistent_wall_clock(stamp, zone):
    with pytest.raises(ValueError):
        hotel_moment(stamp, zone)
