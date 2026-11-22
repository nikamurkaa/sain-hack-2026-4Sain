"""Сервер команды team25. Контракт проверки и клиентский API."""
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Literal
from datetime import timedelta
from zoneinfo import ZoneInfo
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from backend.clients import ModelClient
from backend.api_models import RunAnswer, SessionCreated, Conversation, PreparedView, Guest, Scenario, Catalog, State, MessageResult, Transcription
from backend.core import ServiceError, moment, hotel_moment, check_values
from backend.runner import open_solution
from backend.commands import _local_alarm, success_text, Refusal

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False, limits=httpx.Limits(max_connections=10)) as http:
        app.state.http = http
        app.state.model = ModelClient(http)
        app.state.run_lock = asyncio.Lock()
        app.state.run_cache = {}
        app.state.sessions = {}
        app.state.create_lock = asyncio.Lock()
        app.state.final_session = None
        app.state.speech_lock = asyncio.Lock()
        yield


app = FastAPI(title='Сэйн — умный номер', version='0.1.0', lifespan=lifespan)


@app.middleware('http')
async def private_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/') or request.url.path == '/run':
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(ServiceError)
async def service_error(request, exc):
    content = {'status': 'error', 'code': exc.code, 'message': exc.message}
    # Expose only bounded, non-sensitive action reconciliation metadata.
    if isinstance(getattr(exc, 'operation_id', None), str):
        content['operation_id'] = exc.operation_id
        content['confirmed_devices'] = list(getattr(exc, 'confirmed_devices', ()))[:6]
    return JSONResponse(status_code=exc.status, content=content)


def bearer(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith('Bearer ') or not authorization[7:].strip():
        raise ServiceError('AUTH_REQUIRED', 'Нужен заголовок Authorization: Bearer.', 401)
    return authorization[7:].strip()


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    case: Literal[2]
    dataset_code: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')


@app.get('/')
@app.get('/health')
async def health():
    return {'team': os.getenv('TEAM', 'team25'), 'status': 'ok'}


@app.post('/run', response_model=RunAnswer)
async def run(body: RunInput, token=Depends(bearer)):
    key = hashlib.sha256((token + '\0' + body.dataset_code).encode()).hexdigest()
    if app.state.run_lock.locked():
        raise ServiceError('RUN_BUSY', 'Уже выполняется прогон. Дождитесь его завершения.', 409)
    async with app.state.run_lock:
        now = time.monotonic()
        app.state.run_cache = {k: v for k, v in app.state.run_cache.items() if now - v[0] < 2700}
        if key in app.state.run_cache:
            cached = app.state.run_cache[key][1]
            if isinstance(cached, ServiceError):
                raise ServiceError(cached.code, cached.message, cached.status)
            return cached
        if len(app.state.run_cache) >= 4:
            del app.state.run_cache[next(iter(app.state.run_cache))]
        # Даже при отмене HTTP-запроса повтор не переисполнит относительные команды.
        app.state.run_cache[key] = (now, ServiceError('RUN_UNCERTAIN', 'Предыдущий прогон не завершился. Нужен новый dev-прогон или проверка журнала.', 409))
        try:
            async with asyncio.timeout(2640):
                solution = await open_solution(token, body.dataset_code, app.state.http, app.state.model, os.getenv('HACK_TEAM_TOKEN'))
                if solution.data['meta']['phase'] == 'final':
                    app.state.final_session = None
                result = await solution.run()
                if solution.data['meta']['phase'] == 'final' and len(solution.data['stays']) == 1:
                    stay = solution.data['stays'][0]
                    prepared = solution.prepared.get(stay['record_id'])
                    app.state.final_session = None
                    if prepared is not None:
                        room, prefs, steps = prepared
                        app.state.final_session = FinalPresentation(
                            room, stay, prefs, steps, solution.user(stay['user_id']),
                            {'devices': solution.data['devices'], 'tracks': solution.data['tracks']})
        except TimeoutError:
            raise ServiceError('RUN_TIMEOUT', 'Превышено время обработки набора.', 504) from None
        except ServiceError as exc:
            app.state.run_cache[key] = (time.monotonic(), ServiceError(exc.code, exc.message, exc.status))
            raise
        app.state.run_cache[key] = (time.monotonic(), result)
        return result


class SessionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_code: str = Field(default='case2-dev-v1', pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')
    stay_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')
    source: Literal['dev', 'final'] = 'dev'


class DeviceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    device_id: Literal['light', 'climate', 'sound', 'curtains', 'alarm', 'dnd']
    values: dict[str, JsonValue] = Field(min_length=1)
    at: str

    @field_validator('at')
    @classmethod
    def validate_time(cls, value):
        moment(value)
        return value


class MessageInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=2000)
    at: str

    @field_validator('text')
    @classmethod
    def validate_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Введите просьбу.')
        return value

    @field_validator('at')
    @classmethod
    def validate_time(cls, value):
        moment(value)
        return value


@dataclass(frozen=True)
class FinalPresentation:
    room: object
    stay: dict
    prefs: dict
    steps: list
    profile: dict
    catalog: dict


@dataclass
class ClientSession:
    solution: object
    room: object
    prefs: dict
    steps: list
    stay: dict
    expires: float
    at: str
    read_only: bool = False
    presentation: FinalPresentation | None = None
    connection_status: str = 'unchecked'
    last_confirmed: dict | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    messages: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


def client_session(token=Depends(bearer)):
    key = hashlib.sha256(token.encode()).hexdigest()
    session = app.state.sessions.get(key)
    outdated = session and session.presentation and session.presentation is not app.state.final_session
    if not session or outdated or session.expires <= time.monotonic():
        app.state.sessions.pop(key, None)
        raise ServiceError('SESSION_EXPIRED', 'Сеанс не найден или истёк. Создайте новый.', 401)
    return session


@app.post('/api/v1/sessions', status_code=201, response_model=SessionCreated)
async def create_session(body: SessionInput, token=Depends(bearer)):
    # Служебный маршрут: upstream-токен не нужен браузеру.
    expected = os.getenv('HACK_TEAM_TOKEN', '')
    if not expected or not hmac.compare_digest(token, expected):
        raise ServiceError('ACCESS_DENIED', 'Создание демонстрационного сеанса доступно команде.', 403)
    async with app.state.create_lock:
        app.state.sessions = {k: s for k, s in app.state.sessions.items() if s.expires > time.monotonic()}
        if len(app.state.sessions) >= 8:
            raise ServiceError('SESSION_LIMIT', 'Достигнут лимит активных сеансов.', 429)
        if body.source == 'final':
            view = app.state.final_session
            if view is None:
                raise ServiceError('FINAL_NOT_READY', 'Финальный пользователь ещё не подготовлен.', 409)
            if body.stay_id is not None and body.stay_id != view.stay['record_id']:
                raise ServiceError('STAY_NOT_FOUND', 'Проживание не найдено.', 404)
            session = ClientSession(None, view.room, view.prefs, view.steps, view.stay,
                                    time.monotonic() + 1800, view.stay['check_in_at'],
                                    read_only=True, presentation=view)
        else:
            if body.stay_id is None:
                raise ServiceError('STAY_REQUIRED', 'Для dev-сеанса укажите stay_id.', 422)
            solution = await open_solution(token, body.dataset_code, app.state.http, app.state.model, expected)
            try:
                stay = solution.stay(body.stay_id)
            except StopIteration:
                raise ServiceError('STAY_NOT_FOUND', 'Проживание не найдено.', 404) from None
            if not solution.run_id or solution.run_deadline is None:
                raise ServiceError('DEV_RUN_REQUIRED', 'Не подтверждён отдельный dev-прогон.', 502)
            room, prefs, steps = await solution.prepare(stay)
            session = ClientSession(solution, room, prefs, steps, stay, solution.run_deadline, stay['check_in_at'])
        remaining = int(session.expires - time.monotonic())
        if remaining <= 0:
            raise ServiceError('SESSION_EXPIRED', 'Прогон истёк во время подготовки номера.', 409)
        key = secrets.token_urlsafe(32)
        app.state.sessions[hashlib.sha256(key.encode()).hexdigest()] = session
        return {'session_token': key, **session_info(session)}


def session_info(session):
    actions = ['guest', 'scenario', 'catalog', 'prepared']
    if session.connection_status != 'access_ended':
        actions.append('state')
    can_send = not session.read_only and session.connection_status != 'access_ended'
    if can_send:
        actions.extend(['message', 'transcription', 'devices'])
    return {'source': 'final' if session.presentation else 'dev',
            'connection_status': session.connection_status, 'can_send_requests': can_send,
            'actions': actions, 'expires_in': max(0, int(session.expires - time.monotonic())),
            'read_only': not can_send, 'stay_id': session.stay['record_id'],
            'mode': 'simulator', 'at': session.at, 'until': session.room.session['until']}


@app.get('/api/v1/session', response_model=Conversation)
async def conversation(session=Depends(client_session)):
    async with session.lock:
        return {**session_info(session), 'history': list(session.history)}


def guest_data(session):
    uid = session.stay['user_id']
    profile = session.presentation.profile if session.presentation else session.solution.user(uid)
    display_fields = ('timezone', 'chronotype', 'goal', 'weekday_bedtime', 'weekday_wake_time', 'sleep_preferences')
    return {'user_id': uid, 'stay': session.stay, 'preferences': session.prefs,
            'profile': {key: profile.get(key) for key in display_fields}}


@app.get('/api/v1/guest', response_model=Guest)
async def guest(session=Depends(client_session)):
    return guest_data(session)


@app.get('/api/v1/prepared', response_model=PreparedView)
async def prepared_view(session=Depends(client_session)):
    return {'source': 'final' if session.presentation else 'dev', 'provenance': 'prepared',
            'guest': guest_data(session), 'scenario': {'steps': session.steps},
            'last_confirmed': session.last_confirmed}


@app.get('/api/v1/scenario', response_model=Scenario)
async def scenario(session=Depends(client_session)):
    return {'steps': session.steps}


@app.get('/api/v1/catalog', response_model=Catalog)
async def catalog(session=Depends(client_session)):
    if session.presentation:
        return session.presentation.catalog
    return {'devices': session.solution.data['devices'], 'tracks': session.solution.data['tracks']}


def check_time(session, at):
    try:
        zone = session.stay.get('hotel_timezone')
        value = hotel_moment(at, zone) if zone else moment(at)
    except (ValueError, KeyError):
        raise ServiceError('INVALID_TIME',
                           'Дата, время или UTC-offset не совпадают с часовым поясом отеля.', 422) from None
    if not moment(session.room.session['from']) <= value <= moment(session.room.session['until']):
        raise ServiceError('TIME_OUTSIDE_SESSION', 'Время выходит за пределы проживания.', 422)


@app.get('/api/v1/state', response_model=State)
async def state(at: str | None = None, session=Depends(client_session)):
    # Explicit ?at= is a read-only virtual preview. It must not replace the
    # confirmed live snapshot used by /prepared and offline UI fallbacks.
    is_preview = at is not None
    at = at or session.at
    try:
        check_time(session, at)
    except ValueError:
        raise ServiceError('INVALID_TIME', 'Нужна дата с явным смещением UTC.', 422) from None
    async with session.lock:
        if session.connection_status == 'access_ended':
            raise ServiceError('LIVE_ACCESS_ENDED', 'Доступ к состоянию завершён.', 403)
        try:
            actual = await session.room.state(at)
        except ServiceError as exc:
            note_upstream_error(session, exc)
            raise
        session.connection_status = 'available'
        snapshot = {'at': at, 'state': actual}
        if not is_preview:
            session.last_confirmed = snapshot
        return snapshot


def note_upstream_error(session, exc):
    if exc.status in (401, 403) or exc.code in ('RUN_EXPIRED', 'RUN_REVOKED'):
        session.connection_status = 'access_ended'
    elif exc.status == 429:
        session.connection_status = 'rate_limited'
    else:
        session.connection_status = 'unavailable'


def require_writable(session):
    if session.expires <= time.monotonic():
        raise ServiceError('SESSION_EXPIRED', 'Срок сеанса истёк.', 401)
    if session.read_only or session.connection_status == 'access_ended':
        raise ServiceError('SESSION_READ_ONLY', 'В этом сеансе управление недоступно.', 409)


@app.post('/api/v1/messages', response_model=MessageResult)
async def message(body: MessageInput, idempotency_key: str = Header(min_length=8, max_length=128), session=Depends(client_session)):
    fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    async with session.lock:
        if idempotency_key in session.messages:
            old = session.messages[idempotency_key]
            if old[0] != fingerprint:
                raise ServiceError('IDEMPOTENCY_CONFLICT', 'Этот ключ уже использован для другого сообщения.', 409)
            if isinstance(old[1], ServiceError):
                # Keep ActionFailure metadata (confirmed devices + operation ID).
                # Recreating a plain ServiceError erased the partial result.
                raise old[1]
            return old[1]
        require_writable(session)
        if len(session.messages) >= 100:
            raise ServiceError('MESSAGE_LIMIT', 'Лимит сообщений сеанса исчерпан.', 429)
        check_time(session, body.at)
        if moment(body.at) < moment(session.at):
            raise ServiceError('TIME_BACKWARDS', 'Нельзя отправить команду раньше предыдущей.', 409)
        uncertain = ServiceError('MESSAGE_UNCERTAIN', 'Результат не подтверждён. Проверьте состояние комнаты.', 409)
        session.messages[idempotency_key] = (fingerprint, uncertain)
        try:
            texts = [body.text]
            reply, actual = await session.solution.message(session.room, session.stay['user_id'], texts, body.at,
                                                           history=session.history)
            result = {'reply': reply, 'state': actual}
            session.connection_status = 'available'
            session.last_confirmed = {'at': body.at, 'state': actual}
            session.at = body.at
            session.history.append({'at': body.at, 'utterances': texts, 'reply': reply})
            session.messages[idempotency_key] = (fingerprint, result)
            return result
        except ServiceError as exc:
            if exc.code.startswith(('UPSTREAM_', 'RUN_')):
                note_upstream_error(session, exc)
                if exc.status == 409:
                    session.read_only = True
            session.messages[idempotency_key] = (fingerprint, exc)
            raise


@app.post('/api/v1/devices', response_model=MessageResult)
async def set_device(body: DeviceInput, idempotency_key: str = Header(min_length=8, max_length=128),
                     session=Depends(client_session)):
    """Manual controls in an authorized writable dev session only."""
    fingerprint = hashlib.sha256(('manual:' + body.model_dump_json()).encode()).hexdigest()
    async with session.lock:
        previous = session.messages.get(idempotency_key)
        if previous:
            if previous[0] != fingerprint:
                raise ServiceError('IDEMPOTENCY_CONFLICT', 'Ключ уже использован для другой настройки.', 409)
            if isinstance(previous[1], ServiceError):
                raise previous[1]
            return previous[1]
        require_writable(session)
        if len(session.messages) >= 100:
            raise ServiceError('MESSAGE_LIMIT', 'Лимит операций сеанса исчерпан.', 429)
        check_time(session, body.at)
        if moment(body.at) < moment(session.at):
            raise ServiceError('TIME_BACKWARDS', 'Нельзя изменять настройки в прошлом.', 409)
        changes = dict(body.values)
        if body.device_id == 'alarm' and isinstance(changes.get('at'), str) and len(changes['at']) == 5:
            try:
                hotel = session.stay.get('hotel_timezone')
                zone = ZoneInfo(hotel) if hotel else moment(body.at).tzinfo
                now = moment(body.at).astimezone(zone)
                when = _local_alarm(now.date(), changes['at'], zone)
                if when.astimezone(ZoneInfo('UTC')) <= now.astimezone(ZoneInfo('UTC')):
                    when = _local_alarm(now.date() + timedelta(days=1), changes['at'], zone)
                changes['at'] = when.isoformat()
            except Refusal as exc:
                # A DST gap/fold is a user-domain refusal, not a server fault.
                # Reserve the idempotency key even on rejection: same payload
                # replays identical 422; a different payload conflicts.
                error = ServiceError('INVALID_TIME', str(exc), 422)
                session.messages[idempotency_key] = (fingerprint, error)
                raise error from None
            except (ValueError, KeyError, OverflowError):
                error = ServiceError('INVALID_TIME', 'Укажите допустимое время пробуждения.', 422)
                session.messages[idempotency_key] = (fingerprint, error)
                raise error from None
        try:
            check_values(session.solution.data['devices'], body.device_id, changes)
        except (JsonSchemaValidationError, ValueError, TypeError):
            raise ServiceError('INVALID_VALUE', 'Значение не соответствует настройкам устройства.', 422) from None
        uncertain = ServiceError('ACTION_UNCERTAIN', 'Результат не подтверждён. Проверьте состояние номера.', 409)
        session.messages[idempotency_key] = (fingerprint, uncertain)
        command = {'device_id': body.device_id, 'values': changes, 'at': body.at}
        try:
            actual = await session.room.execute([command], body.at)
        except ServiceError as exc:
            note_upstream_error(session, exc)
            if exc.status == 409 and exc.code.startswith(('UPSTREAM_', 'RUN_')):
                session.read_only = True
            session.messages[idempotency_key] = (fingerprint, exc)
            raise
        reply = {'role': 'agent', 'at': body.at,
                 'text': success_text([command], session.solution.data['tracks']), 'response_class': 'done'}
        result = {'reply': reply, 'state': actual}
        session.connection_status = 'available'
        session.last_confirmed = {'at': body.at, 'state': actual}
        session.at = body.at
        session.history.append({'at': body.at, 'utterances': ['Ручная настройка: ' + body.device_id],
                                'reply': reply})
        session.messages[idempotency_key] = (fingerprint, result)
        return result


@app.delete('/api/v1/session', status_code=204)
async def close_session(token=Depends(bearer)):
    app.state.sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)



AUDIO_TYPES = {
    'audio/webm': 'webm', 'audio/mp4': 'm4a', 'audio/m4a': 'm4a',
    'audio/x-m4a': 'm4a', 'audio/mpeg': 'mp3', 'audio/mp3': 'mp3',
    'audio/wav': 'wav', 'audio/x-wav': 'wav', 'audio/ogg': 'ogg',
    'audio/flac': 'flac', 'audio/x-flac': 'flac',
}
MAX_AUDIO_BYTES = 5_000_000  # Лимит байтов самого файла, без служебных полей multipart.


@app.post('/api/v1/transcriptions', response_model=Transcription, responses={
    402: {'description': 'Дневной бюджет распознавания исчерпан до 00:00 МСК.'},
    413: {'description': 'Аудиофайл превышает 5 000 000 байт.'},
    415: {'description': 'Формат записи не поддерживается.'},
    429: {'description': 'Распознавание занято или достигнут лимит частоты.'},
}, openapi_extra={
    'requestBody': {'required': True, 'content': {
        media_type: {'schema': {'type': 'string', 'format': 'binary'}}
        for media_type in AUDIO_TYPES
    }}
})
async def transcribe(request: Request, session=Depends(client_session)):
    require_writable(session)
    media_type = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
    if media_type not in AUDIO_TYPES:
        raise ServiceError('AUDIO_TYPE', 'Нужна запись WebM, M4A, MP3, WAV, OGG или FLAC.', 415)
    if app.state.speech_lock.locked():
        raise ServiceError('SPEECH_BUSY', 'Распознаётся другая запись. Попробуйте через несколько секунд.', 429)
    async with app.state.speech_lock:
        try:
            async with asyncio.timeout(180):
                body = bytearray()
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_AUDIO_BYTES:
                        raise ServiceError('AUDIO_TOO_LARGE', 'Запись превышает 5 МБ. Отправьте более короткую просьбу.', 413)
                    body.extend(chunk)
                if not body:
                    raise ServiceError('AUDIO_EMPTY', 'Запись пустая. Повторите запись или введите текст.', 422)
                # Распознавание заполняет поле чата. Команда выполняется обычным /messages.
                text = await app.state.model.transcribe(bytes(body), media_type, AUDIO_TYPES[media_type])
                return {'text': text}
        except TimeoutError:
            raise ServiceError('SPEECH_TIMEOUT', 'Распознавание заняло слишком много времени. Повторите запись.', 504) from None
