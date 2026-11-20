"""Regression tests for repeated relative commands in the isolated local rehearsal."""
import asyncio
from fastapi.testclient import TestClient
from scripts.rehearse_client import RehearsalModel, build_rehearsal
from tests.helpers import AT

def ask(phrase, history):
    return asyncio.run(RehearsalModel().json("intent", {"utterances":[phrase], "history":history}))

def turn(text, status="done"):
    return {"utterances":[text], "reply":{"response_class":status, "text":"ok"}}

def test_context_direction_and_switching():
    for text, intent in (
        ("Сделай попрохладнее", "cooler"), ("Сделай потеплее", "warmer"),
        ("Сделай потише", "quieter"), ("Сделай поярче", "brighter"),
        ("Сделай потемнее", "dimmer")
    ):
        history=[turn(text), turn("Ещё немного"), turn("Ещё немного")]
        assert ask("Ещё немного",history)["intent"]==intent
    assert ask("Ещё немного",[])["intent"]=="out_of_scope"
    assert ask("Ещё немного",[turn("Сделай попрохладнее"),turn("Закрой шторы")])["intent"]=="out_of_scope"
    assert ask("Ещё немного",[turn("Сделай попрохладнее"),turn("Поставь 35 градусов","refused")])["intent"]=="out_of_scope"
    assert ask("Ещё немного",[turn("Сделай попрохладнее"),turn("Сделай потеплее")])["intent"]=="warmer"

def test_rehearsal_fastapi_three_successive_relative_commands():
    with TestClient(build_rehearsal()) as client:
        created=client.post("/api/v1/sessions",headers={"Authorization":"Bearer offline-team"},
                            json={"source":"dev","stay_id":"stay_test"})
        assert created.status_code==201,created.text
        auth={"Authorization":"Bearer "+created.json()["session_token"]}
        initial=client.get("/api/v1/state",headers=auth).json()["state"]["climate"]["temperature_c"]
        for n,phrase in enumerate(("Сделай попрохладнее","Ещё немного","Ещё немного"),1):
            response=client.post("/api/v1/messages",headers={**auth,"Idempotency-Key":f"context-test-{n}"},
                                 json={"text":phrase,"at":AT})
            assert response.status_code==200,response.text
            result=response.json()
            assert result["reply"]["response_class"]=="done"
            assert result["state"]["climate"]["temperature_c"]==initial-n
        history=client.get("/api/v1/session",headers=auth).json()["history"]
        assert [h["utterances"] for h in history]==[
            ["Сделай попрохладнее"],["Ещё немного"],["Ещё немного"]
        ]
