"""Loopback-only browser rehearsal. Run python -m scripts.rehearse_client."""
import os
import re
import json
import asyncio
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI

from scripts.offline_guard import FAKE_ENV
from tests.helpers import CATALOG, FakeModel
from tests.offline_cases import CASES
from tests.simulator import Simulator
from backend.clients import ModelClient


class RehearsalModel(FakeModel):
    def __init__(self, faults=None):
        self.faults = faults

    async def json(self, instruction, payload, output_tokens=3500):
        if "utterances" not in payload:
            return {"facts": []}
        phrase = payload["utterances"][-1]
        # These deterministic phrases exist ONLY in loopback REHEARSAL.
        # No official client, token, API or user-controlled fault endpoint.
        synthetic_faults = {
            "Проверка частичного выполнения": "partial",
            "Проверка частичного выполнения без состояния": "partial_stale",
            "Проверка конфликта состояния": "conflict",
            "Проверка неопределённого результата": "uncertain",
            "Проверка отмены после принятия": "cancel_after_commit_stale",
            "Проверка отмены составной команды": "multi_no_fault",
        }
        if self.faults is not None and phrase in synthetic_faults:
            self.faults["mode"] = synthetic_faults[phrase]
            return {"intent": "all_off"}
        if phrase.casefold().strip(" .!?…") in ("ещё немного", "еще немного", "ещё", "еще"):
            # Continue the last *successful* direction, including consecutive continuations.
            # An unrelated/refused request breaks the chain to prevent unintended changes.
            directions = {
                "сделай попрохладнее": "cooler", "попрохладнее": "cooler",
                "душно": "cooler", "сделай потеплее": "warmer",
                "потеплее": "warmer", "холодно": "warmer",
                "сделай потише": "quieter", "потише": "quieter",
                "убавь звук": "quieter", "сделай поярче": "brighter",
                "поярче": "brighter", "добавь света": "brighter",
                "сделай потемнее": "dimmer", "потемнее": "dimmer",
                "убавь свет": "dimmer",
            }
            for exchange in reversed(payload.get("history") or []):
                if exchange.get("reply", {}).get("response_class") != "done":
                    break
                previous = exchange.get("utterances", [""])[-1].casefold().strip(" .!?…")
                if previous in ("ещё немного", "еще немного", "ещё", "еще"):
                    continue
                if previous in directions:
                    return {"intent": directions[previous]}
                break
            return {"intent": "out_of_scope"}
        if phrase.startswith("Установи температуру"):
            number = re.search(r"-?\d+(?:[.,]\d+)?", phrase)
            if number:
                return {"intent": "warmer", "value": float(number[0].replace(",", "."))}
        for prefix, intent in [("Установи яркость", "brighter"), ("Открой шторы на", "curtains"),
                               ("Установи громкость", "quieter")]:
            match = re.fullmatch(prefix + r" (\d+) процентов", phrase)
            if match:
                return {"intent": intent, "value": int(match[1])}
        alarm = re.fullmatch(r"Разбуди меня в (\d\d:\d\d), режим (свет и звук|свет|звук)", phrase)
        if alarm:
            return {"intent": "alarm_set", "time": alarm[1],
                    "mode": {"свет": "light", "звук": "sound", "свет и звук": "both"}[alarm[2]]}
        if phrase in ("Включи режим не беспокоить", "Выключи режим не беспокоить"):
            return {"intent": "do_not_disturb", "enabled": phrase.startswith("Включи")}
        for track in CATALOG["tracks"]:
            if phrase == "Включи звук " + track["title"]:
                return {"intent": "sound_on", "track_id": track["track_id"]}
        for sample, intent, _ in CASES:
            if phrase == sample:
                return intent
        return {"intent": "out_of_scope"}

    async def transcribe(self, audio, media_type, extension):
        if not audio:
            raise ValueError("Empty recording")
        return "Сделай попрохладнее"


def build_rehearsal(*, live=False):
    if live:
        # Only organizer credentials stay in the local operator environment.
        # The room is still our isolated, synthetic simulator.
        if not os.getenv('LLM_API_KEY') or not os.getenv('LLM_MODEL'):
            raise RuntimeError('LIVE mode requires LLM_API_KEY and LLM_MODEL in local environment')
        os.environ.update({key: value for key, value in FAKE_ENV.items()
                           if not key.startswith('LLM_')})
    else:
        os.environ.update(FAKE_ENV)
    from main import app as backend

    dev, final = Simulator(), Simulator()
    final.data["meta"]["phase"] = "final"
    final.data["requests"] = []
    final.data["stays"][0]["record_id"] = "final_stay_test"
    # Give the rehearsal dev guest an afternoon checkout for all four previews.
    dev.until = "2026-11-13T15:00:00+03:00"
    final.data["stays"][0]["user_id"] = final.data["users"][0]["user_id"] = "final_test"
    faults = {"mode": None, "fail_state_reads": 0, "rejections": 0, "injected": 0}
    model = RehearsalModel(faults)

    class SyntheticCancellationHTTP(httpx.AsyncClient):
        """Only loopback MockTransport: inject actual asyncio.CancelledError
        AFTER local simulator accepted a POST. No production behavior altered.
        """
        async def request(self, method, url, **kwargs):
            response = await super().request(method, url, **kwargs)
            if (method.upper() == "POST" and str(url).endswith("/action")
                    and faults["mode"] == "cancel_after_commit_stale"):
                faults["mode"] = None
                faults["fail_state_reads"] = 3
                faults["injected"] += 1
                raise asyncio.CancelledError("synthetic cancelled task after POST commit")
            return response

    def dispatch(request):
        # Faults are synthesized only by the localhost MockTransport for the
        # special test request and NEVER affect the closed official simulator.
        if request.headers.get("authorization") == "Bearer evaluation":
            return final(request)
        path = request.url.path
        if (request.method == "GET" and path.endswith("/state")
                and faults["fail_state_reads"] > 0):
            faults["fail_state_reads"] -= 1
            return httpx.Response(503, json={"code": "SYNTHETIC_STATE_DOWN"})
        if request.method == "POST" and path.endswith("/action") and faults["mode"]:
            body = json.loads(request.content)
            mode, device = faults["mode"], body.get("device_id")
            if mode in ("partial", "partial_stale") and device == "sound":
                faults["mode"] = None
                faults["rejections"] += 1
                faults["injected"] += 1
                if mode == "partial_stale":
                    faults["fail_state_reads"] = 3  # defeat all safe GET retries
                return httpx.Response(409, json={"code": "SYNTHETIC_ACTION_REJECTED"})
            if mode == "uncertain" and device == "light":
                # Upstream commits first POST then loses its reply; the
                # verification GET also fails, so no step is called confirmed.
                response = dev(request)
                faults["mode"] = None
                faults["fail_state_reads"] = 3
                faults["injected"] += 1
                return httpx.Response(503, json={"code": "SYNTHETIC_LOST_REPLY"})
            if mode == "conflict" and device == "sound":
                response = dev(request)
                sid = path.split("/")[2]
                # Other actor's independent device change before reconciliation:
                # the second command's full-state expectation is now false.
                dev.sessions[sid]["entries"].append({
                    "kind": "action", "steps": [{
                        "device_id": "climate",
                        "values": {"temperature_c": 25},
                        "at": body["at"],
                    }]
                })
                faults["mode"] = None
                faults["injected"] += 1
                return response
        return dev(request)

    @asynccontextmanager
    async def lifespan(app):
        async with backend.router.lifespan_context(backend), SyntheticCancellationHTTP(
            transport=httpx.MockTransport(dispatch)
        ) as upstream, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=backend), base_url="http://offline.invalid"
        ) as internal, httpx.AsyncClient(trust_env=False, follow_redirects=False) as provider:
            backend.state.http, backend.state.model = upstream, model
            app.state.rehearsal_faults = faults
            app.state.rehearsal_simulator = dev
            response = await internal.post("/run", headers={"Authorization": "Bearer evaluation"},
                                           json={"case": 2, "dataset_code": "offline-final"})
            response.raise_for_status()
            final.closed = True
            if live:
                # Never use FakeModel for live user messages or microphone STT.
                # Only the synthetic fixture bootstrap above is deterministic.
                backend.state.model = ModelClient(provider)
            yield

    wrapper = FastAPI(lifespan=lifespan)
    @wrapper.middleware("http")
    async def identify_rehearsal(request, call_next):
        response = await call_next(request)
        response.headers["X-Sain-Rehearsal"] = "1"
        return response

    wrapper.mount("/", backend)
    return wrapper


if __name__ == "__main__":
    uvicorn.run(build_rehearsal(), host="127.0.0.1", port=8765, access_log=False)
