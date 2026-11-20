"""Допустимость, арифметика и формирование команд проверяются кодом."""
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from jsonschema.exceptions import ValidationError as SchemaError

from backend.core import check_values, iso, moment
from backend.scheduler import sleep_sound, sleep_temperature


class Refusal(Exception):
    pass


def _local_alarm(date, clock, zone):
    naive = datetime.combine(date, time.fromisoformat(clock))
    first = naive.replace(tzinfo=zone, fold=0)
    second = naive.replace(tzinfo=zone, fold=1)
    valid_first = first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == naive
    valid_second = second.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == naive
    if not valid_first and not valid_second:
        raise Refusal("Это местное время не существует из-за перевода часов. Укажите другое время.")
    if valid_first and valid_second and first.utcoffset() != second.utcoffset():
        raise Refusal("Это время повторяется при переводе часов. Уточните другое время.")
    return first if valid_first else second


def plan_commands(intent, state, prefs, at, devices, tracks, hotel_timezone=None):
    name = intent.intent
    if name == "medical":
        raise Refusal("Я могу управлять настройками номера, но не определяю причины симптомов и не подбираю лекарства. Обратитесь к врачу.")
    if name in ("out_of_scope", "invalid_value"):
        raise Refusal("Эту просьбу выполнить не могу. Доступно управление светом, температурой, звуком, шторами, будильником и режимом «Не беспокоить».")
    if intent.needs_clarification:
        raise Refusal("Уточните, пожалуйста, нужную настройку и значение.")
    changes = {}
    if name in ("brighter", "dimmer", "warmer", "cooler", "quieter"):
        dev, field, step, sign = {
            "brighter": ("light", "brightness", 20, 1), "dimmer": ("light", "brightness", 20, -1),
            "warmer": ("climate", "temperature_c", 1, 1), "cooler": ("climate", "temperature_c", 1, -1),
            "quieter": ("sound", "volume", 10, -1)}[name]
        value = intent.value if intent.value is not None else state[dev][field] + sign * abs(intent.delta if intent.delta is not None else step)
        # Без заданного числа уменьшение до нуля/увеличение до границы допустимо.
        if intent.value is None and intent.delta is None:
            bounds = (16, 26) if dev == "climate" else (0, 100)
            value = max(bounds[0], min(bounds[1], value))
        if value == state[dev][field] and intent.value is None and intent.delta is None:
            raise Refusal("Достигнута граница настройки. Дальше изменить её в эту сторону нельзя.")
        # The LLM may return a syntactically valid absolute value that
        # reverses the user's requested direction. Never execute that.
        before = state[dev][field]
        if (sign > 0 and value <= before) or (sign < 0 and value >= before):
            raise Refusal("Настройка не изменяется в нужную сторону. Уточните значение.")
        changes = {dev: {field: value}}
    elif name == "curtains":
        if intent.value is None:
            raise Refusal("Насколько открыть или закрыть шторы?")
        changes = {"curtains": {"position": intent.value}}
    elif name == "all_off":
        changes = {"light": {"brightness": 0}, "sound": {"volume": 0}}
    elif name == "sound_on":
        track = intent.track_id or (prefs["tracks"][0] if prefs["tracks"] else None)
        if not track:
            raise Refusal("Какой звук включить? Выберите трек из доступного списка.")
        changes = {"sound": {"track_id": track, "volume": min(100, max(state["sound"]["volume"] + 10, prefs["volume"]))}}
    elif name in ("alarm_set", "alarm_shift"):
        zone = ZoneInfo(hotel_timezone) if hotel_timezone else moment(at).tzinfo
        now = moment(at).astimezone(zone)
        if name == "alarm_set":
            if intent.after_minutes is not None:
                if intent.time is not None or intent.day_offset is not None:
                    raise Refusal("Укажите либо конкретное время, либо интервал.")
                alarm = (now.astimezone(timezone.utc) + timedelta(minutes=intent.after_minutes)).astimezone(zone)
            else:
                if intent.time is None:
                    raise Refusal("На какое время поставить будильник?")
                offset = intent.day_offset or 0
                alarm = _local_alarm(now.date() + timedelta(days=offset), intent.time, zone)
                if intent.day_offset is None and alarm <= now:
                    alarm = _local_alarm(now.date() + timedelta(days=1), intent.time, zone)
                elif intent.day_offset is not None and alarm <= now:
                    raise Refusal("Указанное время будильника уже прошло.")
        else:
            if state["alarm"]["at"] is None or intent.delta is None:
                raise Refusal("Укажите время будильника: сейчас нечего сдвигать или не указан интервал.")
            try:
                alarm = (moment(state["alarm"]["at"]).astimezone(timezone.utc)
                         + timedelta(minutes=intent.delta)).astimezone(zone)
            except OverflowError:
                raise Refusal("Слишком большой интервал сдвига будильника.") from None
            if alarm <= now:
                raise Refusal("Новое время будильника уже прошло. Укажите будущее время.")
        changes = {"alarm": {"at": iso(alarm)}}
        if intent.mode is not None:
            changes["alarm"]["mode"] = intent.mode
    elif name == "alarm_cancel":
        changes = {"alarm": {"at": None}}
    elif name == "do_not_disturb":
        changes = {"dnd": {"enabled": True if intent.enabled is None else intent.enabled}}
    elif name == "going_to_bed":
        changes = {"light": {"brightness": 0}, "curtains": {"position": 0}, "dnd": {"enabled": True},
                   "climate": {"temperature_c": sleep_temperature(prefs)}, "sound": sleep_sound(prefs)}
    elif name == "woke_up":
        changes = {"alarm": {"at": None}, "dnd": {"enabled": False},
                   "light": {"brightness": 70, "color_temperature_k": 4000}}
        for dev, fields in prefs["morning"].items():
            changes.setdefault(dev, {}).update(fields)
    elif name in ("like_home", "like_yesterday"):
        changes = deepcopy(prefs["home" if name == "like_home" else "yesterday"])
        if not changes:
            raise Refusal("В доступной истории нет этих настроек. Уточните, что нужно установить.")
    else:
        raise Refusal("Не удалось определить действие.")
    try:
        for dev, fields in changes.items():
            check_values(devices, dev, fields)
    except SchemaError as exc:
        if exc.validator in ("minimum", "maximum"):
            low, high = exc.schema.get("minimum"), exc.schema.get("maximum")
            if low is not None and high is not None:
                raise Refusal(f"Значение {exc.instance} вне допустимого диапазона от {low} до {high}. Выберите значение в этих пределах.") from None
        raise Refusal("Значение не соответствует допустимым настройкам устройства. Выберите другое значение.") from None
    except ValueError:
        raise Refusal("Указанное устройство или настройка недоступны.") from None
    return [{"device_id": dev, "values": fields, "at": at} for dev, fields in changes.items()]


def success_text(commands, tracks=()):
    labels = {"light": "Свет", "climate": "Климат", "sound": "Звук", "curtains": "Шторы",
              "alarm": "Будильник", "dnd": "Не беспокоить"}
    fields = {"brightness": "яркость", "color_temperature_k": "цветовая температура", "temperature_c": "температура",
              "track_id": "трек", "volume": "громкость", "timer_minutes": "таймер", "position": "открытие",
              "at": "время", "mode": "режим", "window_minutes": "окно пробуждения", "enabled": "режим"}
    units = {"brightness": "%", "color_temperature_k": " K", "temperature_c": " °C",
             "volume": "%", "timer_minutes": " мин", "position": "%", "window_minutes": " мин"}
    modes = {"light": "свет", "sound": "звук", "both": "свет и звук"}
    track_names = {track["track_id"]: track["title"] for track in tracks}

    def human(field, value):
        if value is None:
            return "не задано"
        if type(value) is bool:
            return "включён" if value else "выключен"
        if field == "at":
            return moment(value).strftime("%H:%M")
        if field == "track_id":
            return track_names.get(value, value)
        return modes.get(value, str(value)) + units.get(field, "")

    descriptions = []
    for command in commands:
        details = ", ".join(fields[field] + " " + human(field, value)
                            for field, value in command["values"].items())
        descriptions.append(labels[command["device_id"]] + " — " + details)
    return "Готово. " + ". ".join(descriptions) + "."
