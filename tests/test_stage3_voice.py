"""Offline contract regression ONLY. Not evidence of provider success."""
import asyncio
import httpx
import pytest

from backend.clients import ModelClient
from backend.core import ServiceError
from main import SpeechInput


def test_speech_requires_existing_reply_index():
    assert SpeechInput.model_validate({"reply_index": 0}).reply_index == 0
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SpeechInput.model_validate({"reply_index": -1})
    with pytest.raises(ValidationError):
        SpeechInput.model_validate({"reply_index": "0"})


def test_real_tts_adapter_http_contract(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-test-key")
    requests = []
    def handler(request):
        requests.append((request.method, request.url.path))
        assert request.url.path == "/v1/audio/speech"
        assert b'"model":"tts-1"' in request.content
        assert b'"voice":"alloy"' in request.content
        return httpx.Response(200, headers={"content-type": "audio/mpeg"},
                              content=b"ID3" + bytes(500))

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await ModelClient(http).speak("Действие выполнено.")
    sound = asyncio.run(exercise())
    assert sound.startswith(b"ID3")
    assert requests == [("POST", "/v1/audio/speech")]


def test_tts_malformed_response_fails_closed(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-test-key")
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda _: httpx.Response(200, content=b"<html>"))) as http:
            with pytest.raises(ServiceError) as error:
                await ModelClient(http).speak("Подтверждённый ответ")
            assert error.value.code == "TTS_FORMAT"
    asyncio.run(exercise())


@pytest.mark.parametrize("status,code", [(402,"TTS_BUDGET"), (429,"TTS_LIMIT"),
                                          (401,"TTS_UNAVAILABLE"),(503,"TTS_UNAVAILABLE")])
def test_tts_errors_are_not_success(monkeypatch,status,code):
    monkeypatch.setenv("LLM_API_KEY", "fake-test-key")
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda _: httpx.Response(status))) as http:
            with pytest.raises(ServiceError) as error:
                await ModelClient(http).speak("Ответ")
            assert error.value.code == code
    asyncio.run(exercise())


def test_live_bootstrap_preserves_real_model_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-provider-key")
    monkeypatch.setenv("LLM_MODEL", "gpt-6-luna")
    from scripts.rehearse_client import build_rehearsal
    wrapper = build_rehearsal(live=True)
    assert wrapper is not None
    assert __import__("os").environ["LLM_API_KEY"] == "test-provider-key"
    assert __import__("os").environ["LLM_MODEL"] == "gpt-6-luna"
