"""MR-002: manual alarm DST rejects invalid wall time through REAL FastAPI TestClient."""
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from backend.core import moment
from main import app
from tests.test_integration import insert_session


def session_at(token, clock, zone):
    session = insert_session(token)
    session.at = clock
    session.stay = {**session.stay, "hotel_timezone": zone, "check_in_at": clock}
    session.room.session = {
        **session.room.session, "from": clock,
        "until": (moment(clock).astimezone(timezone.utc) + timedelta(days=3)).isoformat(),
    }
    return session


def put_alarm(api, token, key, at, alarm):
    return api.post(
        "/api/v1/devices",
        headers={"Authorization": "Bearer " + token, "Idempotency-Key": key},
        json={"device_id": "alarm", "values": {"at": alarm}, "at": at},
    )


@pytest.mark.parametrize("zone,at,alarm", [
    ("Europe/Berlin", "2026-03-29T01:30:00+01:00", "02:30"),
    ("Europe/Berlin", "2026-10-25T01:30:00+02:00", "02:30"),
    ("America/New_York", "2026-03-08T01:30:00-05:00", "02:30"),
    ("America/New_York", "2026-11-01T00:30:00-04:00", "01:30"),
])
def test_manual_invalid_wall_time_is_controlled_repeatable_422_with_no_post(zone, at, alarm):
    with TestClient(app, raise_server_exceptions=False) as api:
        token = "mr002-" + zone.split("/")[-1] + alarm.replace(":", "")
        session = session_at(token, at, zone)
        before = dict(session.room.actual["alarm"])
        first = put_alarm(api, token, "alarm-invalid-1234", at, alarm)
        second = put_alarm(api, token, "alarm-invalid-1234", at, alarm)
        assert first.status_code == second.status_code == 422, (first.text, second.text)
        assert first.json() == second.json()
        assert first.json()["code"] == "INVALID_TIME"
        assert first.json()["message"]
        assert session.room.executions == 0
        assert session.room.actual["alarm"] == before
        changed = put_alarm(api, token, "alarm-invalid-1234", at, "04:30")
        assert changed.status_code == 409 and changed.json()["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize("zone,at,clock,expected_day", [
    ("Europe/Moscow", "2026-11-13T01:30:00+03:00", "06:40", 13),
    ("Europe/Berlin", "2026-03-29T01:30:00+01:00", "03:30", 29),
    ("Europe/Berlin", "2026-10-25T03:00:00+01:00", "03:30", 25),
    ("America/New_York", "2026-03-08T03:00:00-04:00", "03:30", 8),
    ("America/New_York", "2026-11-01T02:00:00-05:00", "02:30", 1),
    ("Europe/Berlin", "2026-03-29T03:45:00+02:00", "03:30", 30),
])
def test_manual_valid_alarm_is_confirmed_and_replay_safe(zone, at, clock, expected_day):
    with TestClient(app, raise_server_exceptions=False) as api:
        token = "mr002-valid-" + zone.split("/")[-1] + clock.replace(":", "")
        session = session_at(token, at, zone)
        initial_climate = dict(session.room.actual["climate"])
        first = put_alarm(api, token, "alarm-valid-1234", at, clock)
        assert first.status_code == 200, first.text
        alarm = moment(first.json()["state"]["alarm"]["at"]).astimezone(ZoneInfo(zone))
        assert alarm.day == expected_day and alarm.strftime("%H:%M") == clock
        assert first.json()["reply"]["response_class"] == "done"
        repeated = put_alarm(api, token, "alarm-valid-1234", at, clock)
        assert repeated.status_code == 200 and repeated.json() == first.json()
        assert session.room.executions == 1
        assert session.room.actual["climate"] == initial_climate
