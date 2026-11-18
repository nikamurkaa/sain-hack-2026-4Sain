"""Общие проверки времени, данных и параметров устройств."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from functools import lru_cache
import json
import math
import re

from jsonschema import Draft202012Validator, FormatChecker


class ServiceError(Exception):
    def __init__(self, code: str, message: str, status: int = 502):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def moment(value: str) -> datetime:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}", value):
        raise ValueError("Нужна дата со смещением UTC, например 2026-11-12T22:00:00+03:00")
    return datetime.fromisoformat(value)


def iso(value: datetime) -> str:
    if value.utcoffset() is None:
        raise ValueError("Не указан часовой пояс")
    return value.isoformat(timespec="seconds")


@lru_cache(maxsize=2)
def schema_validator(name: str):
    schema = json.loads((Path(__file__).parent / "schemas" / (name + ".json")).read_text())
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_schema(name: str, value: dict) -> None:
    if next(schema_validator(name).iter_errors(value), None) is not None:
        raise ServiceError("INVALID_DATA", "Данные не соответствуют схеме " + name)


def check_values(devices: list, device: str, values: dict) -> None:
    catalog = {d["device_id"]: {f["field_id"]: f["value_schema"] for f in d["fields"]} for d in devices}
    if device not in catalog or not values or set(values) - set(catalog[device]):
        raise ValueError("Неизвестное устройство или параметр")
    for key, value in values.items():
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Число должно быть конечным")
        Draft202012Validator(catalog[device][key], format_checker=FormatChecker()).validate(value)


def default_state(devices: list) -> dict:
    return {d["device_id"]: {f["field_id"]: deepcopy(f["default_value"]) for f in d["fields"]} for d in devices}


def evidence(dataset: dict, user_id: str, cutoff: str) -> list[dict]:
    """Идентификаторы сообщений уникальны только внутри пользователя."""
    bound = moment(cutoff)
    items = []
    for m in dataset["chat_history"]:
        if m["user_id"] == user_id and m["role"] == "user" and moment(m["at"]) <= bound:
            items.append({"id": "chat:" + m["message_id"], "at": m["at"], "text": m["text"], "source": "chat"})
    for e in dataset["events"]:
        if e["user_id"] != user_id or moment(e["started_at"]) > bound:
            continue
        if e.get("ended_at") and moment(e["ended_at"]) > bound:
            continue
        if e.get("payload", {}).get("text"):
            items.append({"id": "event:" + e["event_id"], "at": e["started_at"], "text": e["payload"]["text"], "source": e.get("source", "note")})
    return sorted(items, key=lambda x: moment(x["at"]))
