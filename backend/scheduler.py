"""Расписание по правилам R1–R8 версии gen-case2-draft-2026-11-14."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.core import check_values, iso, moment


def sleep_temperature(prefs):
    return {"cool": 17.5, "neutral": 19.5, "warm": 21.5}[prefs["temperature"]]


def sleep_sound(prefs):
    if not prefs["tracks"]:
        return {"volume": 0}
    return {"track_id": prefs["tracks"][0], "volume": prefs["volume"], "timer_minutes": prefs["timer"]}


def bedtime(user, stay):
    wake = moment(stay["target_wake_at"]).astimezone(ZoneInfo(stay["hotel_timezone"]))
    home = ZoneInfo(user.get("timezone") or stay["hotel_timezone"])
    candidates = []
    for day_shift in range(-2, 2):
        home_bed = datetime.combine(wake.date() + timedelta(days=day_shift),
                                   time.fromisoformat(user.get("weekday_bedtime") or "23:00"), home)
        local_bed = home_bed.astimezone(wake.tzinfo)
        difference = (local_bed.utcoffset() - home_bed.utcoffset()).total_seconds() / 3600
        # Сначала перевод домашнего времени в пояс отеля, затем поправка R8.
        if abs(difference) >= 3:
            local_bed += timedelta(hours=-1 if difference > 0 else 1)
        if local_bed < wake:
            candidates.append(local_bed)
    return max(candidates)


def build_scenario(user, stay, prefs, devices, rules):
    if {r["rule_id"] for r in rules} != {"R" + str(i) for i in range(1, 9)}:
        raise ValueError("Неизвестный набор правил сна")
    # All schedule arithmetic uses absolute instants in UTC, never fixed
    # check-in/wake offsets or ZoneInfo wall-time timedelta arithmetic.
    # Convert each scheduled instant back to the hotel's IANA zone only
    # when serializing it. Otherwise spring-forward yields nonexistent times
    # and fall-back may move events in the wrong chronological order.
    hotel_zone = ZoneInfo(stay["hotel_timezone"])
    start = moment(stay["check_in_at"]).astimezone(timezone.utc)
    wake = moment(stay["target_wake_at"]).astimezone(timezone.utc)
    bed = bedtime(user, stay).astimezone(timezone.utc)
    steps = []

    def add(at, device, values):
        at = max(start, at)
        if at > wake:
            return
        check_values(devices, device, values)
        steps.append({"at": iso(at.astimezone(hotel_zone)), "device_id": device, "values": values})

    evening = max(start, bed - timedelta(minutes=60))
    if start <= bed:
        add(evening, "light", {"brightness": 20, "color_temperature_k": 2700})
    night = max(start, bed)
    add(night, "light", {"brightness": 0})
    add(night, "curtains", {"position": 0})
    add(night, "climate", {"temperature_c": sleep_temperature(prefs)})
    add(night, "dnd", {"enabled": True})
    sound = sleep_sound(prefs)
    sound_start = max(start, bed)  # R4: любимый звук включается непосредственно при отбое.
    add(sound_start, "sound", sound)
    if sound["volume"]:
        add(sound_start + timedelta(minutes=sound["timer_minutes"]), "sound", {"volume": 0, "timer_minutes": 0})
    add(start, "alarm", {"at": iso(wake.astimezone(hotel_zone)), "mode": prefs["alarm_mode"], "window_minutes": 0})
    # R6: three rising light steps within 15–30 minutes before wake, OR
    # open the curtains within that same window. Never backdate an event to
    # before check-in and never silently count two rises as three.
    dawn_steps = [(wake - timedelta(minutes=minutes), brightness)
                  for minutes, brightness in ((30, 10), (23, 30), (16, 60))]
    if all(at >= night for at, _ in dawn_steps):
        for at, brightness in dawn_steps:
            add(at, "light", {"brightness": brightness, "color_temperature_k": 2700})
    elif night <= wake - timedelta(minutes=15):
        # A short stay cannot accommodate three 30/23/16-minute light events.
        # R6 explicitly permits curtains instead; keep R2 darkness until then.
        add(wake - timedelta(minutes=15), "curtains", {"position": 100})
    # If check-in/night begins later than wake - 15 min, the official R6
    # window is already unreachable. Preserve the legal [check-in, wake]
    # timeline instead of fabricating compliance or historical actions.
    add(wake, "dnd", {"enabled": False})
    return sorted(steps, key=lambda x: moment(x["at"]))
