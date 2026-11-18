"""Сервер команды team25. Контракт проверки и клиентский API."""
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
from pathlib import Path
from fastapi.staticfiles import StaticFiles
import logging
import os
import secrets
import time
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.clients import ModelClient
from backend.api_models import RunAnswer, SessionCreated, Guest, Scenario, Catalog, State, MessageResult
from backend.core import ServiceError, moment
from backend.runner import open_solution

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(follow_redirects=False, limits=httpx.Limits(max_connections=10)) as http:
        app.state.http = http
        app.state.model = ModelClient(http)
        app.state.run_lock = asyncio.Lock()
        app.state.run_cache = {}
        app.state.sessions = {}
        app.state.create_lock = asyncio.Lock()
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
    return JSONResponse(status_code=exc.status, content={'status': 'error', 'code': exc.code, 'message': exc.message})


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
                raise cached
            return cached
        if len(app.state.run_cache) >= 4:
            del app.state.run_cache[next(iter(app.state.run_cache))]
        # Даже при отмене HTTP-запроса повтор не переисполнит относительные команды.
        app.state.run_cache[key] = (now, ServiceError('RUN_UNCERTAIN', 'Предыдущий прогон не завершился. Нужен новый dev-прогон или проверка журнала.', 409))
        try:
            async with asyncio.timeout(2640):
                solution = await open_solution(token, body.dataset_code, app.state.http, app.state.model, os.getenv('HACK_TEAM_TOKEN'))
                result = await solution.run()
        except TimeoutError:
            raise ServiceError('RUN_TIMEOUT', 'Превышено время обработки набора.', 504) from None
        except ServiceError as exc:
            app.state.run_cache[key] = (time.monotonic(), exc)
            raise
        app.state.run_cache[key] = (time.monotonic(), result)
        return result


class SessionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_code: str = Field(default='case2-dev-v1', pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')
    stay_id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')


class MessageInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=2000)
    at: str

    @field_validator('at')
    @classmethod
    def validate_time(cls, value):
        moment(value)
        return value


@dataclass
class ClientSession:
    solution: object
    room: object
    prefs: dict
    steps: list
    stay: dict
    expires: float
    at: str
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    messages: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


def client_session(token=Depends(bearer)):
    key = hashlib.sha256(token.encode()).hexdigest()
    session = app.state.sessions.get(key)
    if not session or session.expires <= time.monotonic():
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
        solution = await open_solution(token, body.dataset_code, app.state.http, app.state.model, expected)
        try:
            stay = solution.stay(body.stay_id)
        except StopIteration:
            raise ServiceError('STAY_NOT_FOUND', 'Проживание не найдено.', 404) from None
        room, prefs, steps = await solution.prepare(stay)
        key = secrets.token_urlsafe(32)
        app.state.sessions[hashlib.sha256(key.encode()).hexdigest()] = ClientSession(
            solution, room, prefs, steps, stay, time.monotonic() + 1800, stay['check_in_at'])
        return {'session_token': key, 'expires_in': 1800, 'stay_id': stay['record_id'],
                'at': stay['check_in_at'], 'until': room.session['until'], 'mode': 'simulator'}


@app.get('/api/v1/guest', response_model=Guest)
async def guest(session=Depends(client_session)):
    return {'user_id': session.stay['user_id'], 'stay': session.stay, 'preferences': session.prefs}


@app.get('/api/v1/scenario', response_model=Scenario)
async def scenario(session=Depends(client_session)):
    return {'steps': session.steps}


@app.get('/api/v1/catalog', response_model=Catalog)
async def catalog(session=Depends(client_session)):
    return {'devices': session.solution.data['devices'], 'tracks': session.solution.data['tracks']}


def check_time(session, at):
    value = moment(at)
    if not moment(session.room.session['from']) <= value <= moment(session.room.session['until']):
        raise ServiceError('TIME_OUTSIDE_SESSION', 'Время выходит за пределы проживания.', 422)


@app.get('/api/v1/state', response_model=State)
async def state(at: str | None = None, session=Depends(client_session)):
    at = at or session.at
    try:
        check_time(session, at)
    except ValueError:
        raise ServiceError('INVALID_TIME', 'Нужна дата с явным смещением UTC.', 422) from None
    async with session.lock:
        return {'at': at, 'state': await session.room.state(at)}


@app.post('/api/v1/messages', response_model=MessageResult)
async def message(body: MessageInput, idempotency_key: str = Header(min_length=8, max_length=128), session=Depends(client_session)):
    fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    async with session.lock:
        if idempotency_key in session.messages:
            old = session.messages[idempotency_key]
            if old[0] != fingerprint:
                raise ServiceError('IDEMPOTENCY_CONFLICT', 'Этот ключ уже использован для другого сообщения.', 409)
            if isinstance(old[1], ServiceError):
                raise old[1]
            return old[1]
        if len(session.messages) >= 100:
            raise ServiceError('MESSAGE_LIMIT', 'Лимит сообщений сеанса исчерпан.', 429)
        check_time(session, body.at)
        if moment(body.at) < moment(session.at):
            raise ServiceError('TIME_BACKWARDS', 'Нельзя отправить команду раньше предыдущей.', 409)
        uncertain = ServiceError('MESSAGE_UNCERTAIN', 'Результат не подтверждён. Проверьте состояние комнаты.', 409)
        session.messages[idempotency_key] = (fingerprint, uncertain)
        try:
            texts = ([session.history[-1]['text']] if session.history and session.history[-1]['refused'] else []) + [body.text]
            reply, actual = await session.solution.message(session.room, session.stay['user_id'], texts, body.at)
            result = {'reply': reply, 'state': actual}
            session.at = body.at
            session.history.append({'text': body.text, 'refused': reply['response_class'] == 'refused'})
            session.messages[idempotency_key] = (fingerprint, result)
            return result
        except ServiceError as exc:
            session.messages[idempotency_key] = (fingerprint, exc)
            raise


@app.delete('/api/v1/session', status_code=204)
async def close_session(token=Depends(bearer)):
    app.state.sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)


app.mount('/voice', StaticFiles(directory=Path(__file__).parent / 'frontend' / 'voice', html=True), name='voice')
