"""Explain planned room decisions without confusing plans with confirmed state."""
from datetime import timedelta, timezone
from backend.core import moment
from backend.scheduler import bedtime, sleep_temperature


def preparation_explanations(user, stay, prefs, steps):
    """Safe public reasons: source category only, no raw quotes or source IDs."""
    sources = prefs.get("sources") or {}
    def origin(key):
        fact = sources.get(key)
        if not isinstance(fact, dict):
            return "default", "нейтральная настройка по умолчанию"
        if fact.get("source") == "profile":
            return "profile", "профиль гостя"
        return "history", "его история проживания"
    ts, why_t = origin("temperature")
    ss, why_s = origin("tracks")
    als, why_a = origin("alarm_mode")
    items = [
        dict(device_id="light", source="rules", status="planned",
             reason="R1–R2: приглушённый тёплый свет перед сном, затем темнота."),
        dict(device_id="curtains", source="rules", status="planned",
             reason="R2: закрытые шторы на время сна."),
        dict(device_id="climate", source=ts, status="planned",
             reason=f"R3: на ночь выбрано {sleep_temperature(prefs):g} °C; основание — {why_t}."),
        dict(device_id="sound", source=ss, status="planned",
             reason=("R4: выбран любимый звук; основание — " + why_s + ".")
                    if prefs["tracks"] else "R4: запланирована тишина; основание — " + why_s + "."),
        dict(device_id="alarm", source=als, status="planned",
             reason="R5: подъём по расписанию, режим «" +
                    {"light": "свет", "sound": "звук", "both": "свет и звук"}[prefs["alarm_mode"]] +
                    "»; основание — " + why_a + "."),
        dict(device_id="dnd", source="rules", status="planned",
             reason="R7: «Не беспокоить» включён от отбоя до подъёма."),
        dict(device_id="light", source="rules", status="planned",
             reason="R8: расчётный местный отбой — " + bedtime(user, stay).strftime("%H:%M") + "."),
    ]
    wake = moment(stay["target_wake_at"]).astimezone(timezone.utc)
    def in_window(step):
        instant = moment(step["at"]).astimezone(timezone.utc)
        return wake - timedelta(minutes=30) <= instant <= wake - timedelta(minutes=15)
    lights = [s for s in steps if s["device_id"] == "light"
              and s["values"].get("brightness", 0) > 0 and in_window(s)]
    curtains = any(s["device_id"] == "curtains" and s["values"].get("position", 0) > 10
                   and in_window(s) for s in steps)
    if len(lights) >= 3 or curtains:
        items.append(dict(device_id="light", source="rules", status="planned",
                          reason="R6: рассвет запланирован в официальном временном окне."))
    else:
        items.append(dict(device_id="light", source="rules", status="warning",
                          reason="R6: интервал рассвета 15–30 минут перед подъёмом недоступен. "
                                 "Полное выполнение правила не подтверждено."))
    return items
