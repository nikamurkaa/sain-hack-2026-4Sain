"""Форматы ответов: используются сервером и отображаются в /openapi.json."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, JsonValue


class Output(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Reply(Output):
    role: Literal['agent']
    at: str
    text: str
    response_class: Literal['done', 'refused']


class StayAnswer(Output):
    record_id: str
    session_id: str


class RequestAnswer(StayAnswer):
    replies: list[Reply]


class RunAnswer(Output):
    stays: list[StayAnswer]
    requests: list[RequestAnswer]


class SessionInfo(Output):
    source: Literal['final', 'dev']
    connection_status: Literal['unchecked', 'available', 'unavailable', 'rate_limited', 'access_ended']
    can_send_requests: bool
    actions: list[str]
    expires_in: int
    read_only: bool
    stay_id: str
    at: str
    until: str
    mode: Literal['simulator']


class SessionCreated(SessionInfo):
    session_token: str


class Conversation(SessionInfo):
    history: list[dict[str, JsonValue]]


class Guest(Output):
    user_id: str
    stay: dict[str, JsonValue]
    preferences: dict[str, JsonValue]
    profile: dict[str, JsonValue]


class Step(Output):
    at: str
    device_id: str
    values: dict[str, JsonValue]


class Scenario(Output):
    steps: list[Step]


class Catalog(Output):
    devices: list[dict[str, JsonValue]]
    tracks: list[dict[str, JsonValue]]


class State(Output):
    at: str
    state: dict[str, dict[str, JsonValue]]


class PreparedView(Output):
    source: Literal['final', 'dev']
    provenance: Literal['prepared']
    guest: Guest
    scenario: Scenario
    last_confirmed: State | None


class MessageResult(Output):
    reply: Reply
    state: dict[str, dict[str, JsonValue]]



class Transcription(Output):
    text: str
