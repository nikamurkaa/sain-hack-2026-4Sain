"""Loopback-only browser rehearsal. Run python -m scripts.rehearse_client."""
import os
import re
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI

from scripts.offline_guard import FAKE_ENV
from tests.helpers import CATALOG, FakeModel
from tests.offline_cases import CASES
from tests.simulator import Simulator


class RehearsalModel(FakeModel):
    async def json(self, instruction, payload, output_tokens=3500):
        if "utterances" not in payload:
            return {"facts": []}
        phrase = payload["utterances"][-1]
        if phrase == "Ещё немного" and payload.get("history"):
            previous = payload["history"][-1]["utterances"][-1].lower()
            if "прохлад" in previous or previous == "душно":
                return {"intent": "cooler"}
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


def build_rehearsal():
    os.environ.update(FAKE_ENV)
    from main import app as backend

    dev, final = Simulator(), Simulator()
    final.data["meta"]["phase"] = "final"
    final.data["requests"] = []
    final.data["stays"][0]["user_id"] = final.data["users"][0]["user_id"] = "final_test"

    def dispatch(request):
        sim = final if request.headers["authorization"] == "Bearer evaluation" else dev
        return sim(request)

    @asynccontextmanager
    async def lifespan(app):
        async with backend.router.lifespan_context(backend), httpx.AsyncClient(
            transport=httpx.MockTransport(dispatch)
        ) as upstream, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=backend), base_url="http://offline.invalid"
        ) as internal:
            backend.state.http, backend.state.model = upstream, RehearsalModel()
            response = await internal.post("/run", headers={"Authorization": "Bearer evaluation"},
                                           json={"case": 2, "dataset_code": "offline-final"})
            response.raise_for_status()
            final.closed = True
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
