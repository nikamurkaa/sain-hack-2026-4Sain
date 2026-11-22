"""Клиенты организаторов. Токены и тела ошибок не записываются в журнал."""
import asyncio
from collections import deque
import json
import os
import time

import httpx

from backend.core import ServiceError, validate_schema


class HackClient:
    def __init__(self, token: str, http: httpx.AsyncClient):
        self.token, self.http = token, http
        self.base = os.getenv("HACK_API_URL", "https://hack-api.be-healthy.tech").rstrip("/")
        self.calls = 0

    async def request(self, method: str, path: str, *, body=None, params=None, retry=False):
        # Only safe reads may be retried. A timed-out POST may already have
        # committed upstream even when the response has been lost.
        if retry and method.upper() not in ("GET", "HEAD"):
            raise ServiceError("UNSAFE_RETRY", "Повтор создающей или изменяющей операции запрещён.", 500)
        for attempt in range(3 if retry else 1):
            try:
                self.calls += 1
                response = await self.http.request(method, self.base + path, json=body, params=params,
                                                   headers={"Authorization": "Bearer " + self.token},
                                                   timeout=httpx.Timeout(60, connect=10))
            except httpx.TransportError:
                if retry and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise ServiceError("UPSTREAM_UNCERTAIN", "Сервис не ответил. Результат операции пока не подтверждён.") from None
            if retry and response.status_code in (429, 502, 503, 504) and attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            if response.is_error:
                if method != "GET" and response.status_code >= 500:
                    raise ServiceError("UPSTREAM_UNCERTAIN", "Внешний сервис не подтвердил результат операции.")
                try:
                    error_body = response.json()
                    code = error_body.get("code", "UPSTREAM_ERROR") if isinstance(error_body, dict) else "UPSTREAM_ERROR"
                except ValueError:
                    code = "UPSTREAM_ERROR"
                # Не возвращаем текст внешнего сервиса: в нём могут быть закрытые данные.
                allowed = {"RUN_EXPIRED", "RUN_REVOKED", "RUN_NOT_STARTED"}
                status = response.status_code if response.status_code in (401, 403, 409, 429) else 502
                raise ServiceError(code if isinstance(code, str) and code in allowed else "UPSTREAM_ERROR",
                                   "Сервис организаторов отклонил запрос (HTTP %s)." % response.status_code, status)
            try:
                value = response.json()
                if not isinstance(value, dict):
                    raise ValueError("object required")
                return value
            except ValueError:
                raise ServiceError("UPSTREAM_FORMAT", "Сервис вернул некорректный ответ.") from None

    async def dataset(self, code: str):
        result = await self.request("GET", "/case/2/getData", params={"dataset_code": code}, retry=True)
        data = result.get("dataset")
        # reference принципиально не передаётся остальным частям решения.
        validate_schema("Case2Dataset", data)
        return data

    async def dev_run(self):
        # Для командного токена этап определяется сервером. Поле stage — только admin.
        return await self.request("POST", "/runs", body={"case": 2})


class ModelClient:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http
        self.lock = asyncio.Lock()
        self.next_call = 0.0
        self.speech_starts: deque[float] = deque()
        self.calls = 0
        self.tokens = 0

    def record_usage(self, response):
        if not isinstance(response, dict):
            raise ValueError("object required")
        usage = response.get("usage")
        if isinstance(usage, dict) and type(usage.get("total_tokens")) is int:
            self.tokens += usage["total_tokens"]

    async def wait_for_slot(self, *, speech=False):
        async with self.lock:
            now = time.monotonic()
            if speech:
                while self.speech_starts and self.speech_starts[0] <= now - 60:
                    self.speech_starts.popleft()
                if len(self.speech_starts) >= 10:
                    raise ServiceError("SPEECH_LIMIT", "Лимит частоты распознавания. Повторите через минуту.", 429)
            await asyncio.sleep(max(0, self.next_call - now))
            started = time.monotonic()
            self.next_call = started + 2.2
            if speech:
                self.speech_starts.append(started)

    async def transcribe(self, audio: bytes, media_type: str, extension: str):
        key = os.getenv("LLM_API_KEY")
        if not key:
            raise ServiceError("MODEL_NOT_CONFIGURED", "Не настроен сервис распознавания речи.", 503)
        base = os.getenv("LLM_BASE_URL", "https://bifrost.be-healthy.tech/v1").rstrip("/")
        await self.wait_for_slot(speech=True)
        self.calls += 1
        try:
            response = await self.http.post(
                base + "/audio/transcriptions",
                headers={"Authorization": "Bearer " + key},
                data={"model": "gpt-transcribe", "language": "ru", "response_format": "json"},
                files={"file": ("request." + extension, audio, media_type)},
                timeout=httpx.Timeout(120, connect=10),
            )
        except httpx.TransportError:
            raise ServiceError("SPEECH_UNAVAILABLE", "Не удалось распознать речь. Попробуйте ещё раз.", 503) from None
        if response.status_code == 402:
            raise ServiceError("SPEECH_BUDGET", "Дневной бюджет распознавания исчерпан. Он обновится в 00:00 МСК.", 402)
        if response.status_code == 413:
            raise ServiceError("AUDIO_TOO_LARGE", "Запись превышает 5 МБ. Отправьте более короткую запись.", 413)
        if response.status_code == 429:
            raise ServiceError("SPEECH_LIMIT", "Лимит частоты распознавания. Повторите через минуту.", 429)
        if response.status_code in (400, 415, 422):
            raise ServiceError("INVALID_AUDIO", "Не удалось прочитать запись. Запишите просьбу ещё раз.", 422)
        if response.is_error:
            raise ServiceError("SPEECH_UNAVAILABLE", "Распознавание речи временно недоступно.", 503)
        try:
            raw = response.json()
            text = raw["text"]
            if not isinstance(text, str) or not text.strip() or len(text.strip()) > 2000:
                raise ValueError("invalid transcription")
            self.record_usage(raw)
            return text.strip()
        except (ValueError, KeyError, TypeError):
            raise ServiceError("SPEECH_FORMAT", "Речь не распознана. Повторите запись или введите текст.", 502) from None

    async def json(self, instruction: str, payload: dict, output_tokens=3500):
        key, model = os.getenv("LLM_API_KEY"), os.getenv("LLM_MODEL")
        if not key or not model:
            raise ServiceError("MODEL_NOT_CONFIGURED", "Не настроены LLM_API_KEY и LLM_MODEL.", 503)
        base = os.getenv("LLM_BASE_URL", "https://bifrost.be-healthy.tech/v1").rstrip("/")
        for attempt in range(3):
            await self.wait_for_slot()
            self.calls += 1
            try:
                response = await self.http.post(base + "/chat/completions", headers={"Authorization": "Bearer " + key},
                    json={"model": model, "messages": [{"role": "system", "content": instruction},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                          "max_tokens": output_tokens, "response_format": {"type": "json_object"}}, timeout=120)
            except httpx.TransportError:
                if attempt < 2:
                    await asyncio.sleep(5 * 2 ** attempt)
                    continue
                raise ServiceError("MODEL_UNAVAILABLE", "Не удалось обработать сообщение. Попробуйте позже.", 503) from None
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                delay = 5 * 2 ** attempt
                # A brief server-provided cooldown is more reliable than a
                # blind retry. Bound it so a transient 429 cannot monopolize
                # the official 45-minute /run deadline.
                if response.status_code == 429:
                    try:
                        requested = float(response.headers.get("Retry-After", ""))
                        if 0 < requested <= 60 and requested == requested:
                            delay = max(delay, requested)
                    except ValueError:
                        pass
                await asyncio.sleep(delay)
                continue
            if response.is_error:
                raise ServiceError("MODEL_UNAVAILABLE", "Сервис обработки сообщений временно недоступен.", 503)
            try:
                raw = response.json()
                self.record_usage(raw)
                choice = raw["choices"][0]
                if choice["finish_reason"] != "stop":
                    raise ValueError("incomplete")
                value = json.loads(choice["message"]["content"])
                if not isinstance(value, dict):
                    raise ValueError("object required")
                return value
            except (ValueError, KeyError, IndexError, TypeError):
                raise ServiceError("MODEL_FORMAT", "Не удалось надёжно разобрать сообщение. Уточните просьбу.", 503) from None

