import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.clients import ModelClient
from backend.core import ServiceError
from main import app
from tests.test_integration import insert_session


def test_audio_requires_session_and_does_not_execute_a_command():
    with TestClient(app) as client:
        model = AsyncMock(return_value='Сделай попрохладнее')
        app.state.model.transcribe = model
        headers = {'Content-Type': 'audio/webm;codecs=opus'}
        assert client.post('/api/v1/transcriptions', headers=headers, content=b'audio').status_code == 401
        session = insert_session('guest')
        headers['Authorization'] = 'Bearer guest'
        response = client.post('/api/v1/transcriptions', headers=headers, content=b'audio')
        assert response.status_code == 200
        assert response.json() == {'text': 'Сделай попрохладнее'}
        assert session.room.executions == 0
        assert session.history == []
        model.assert_awaited_once_with(b'audio', 'audio/webm', 'webm')


def test_audio_rejects_empty_unsupported_and_oversized_uploads():
    with TestClient(app) as client:
        insert_session('guest')
        app.state.model.transcribe = AsyncMock()
        headers = {'Authorization': 'Bearer guest', 'Content-Type': 'audio/wav'}
        assert client.post('/api/v1/transcriptions', headers=headers, content=b'').status_code == 422
        assert client.post('/api/v1/transcriptions', headers={**headers, 'Content-Type':'text/plain'}, content=b'text').status_code == 415
        with patch('main.MAX_AUDIO_BYTES', 4):
            assert client.post('/api/v1/transcriptions', headers=headers, content=b'12345').status_code == 413
        app.state.model.transcribe.assert_not_awaited()


@pytest.mark.parametrize('status,expected', [(429,429),(400,422),(401,503),(503,503)])
def test_speech_upstream_errors_are_sanitized(monkeypatch, status, expected):
    monkeypatch.setenv('LLM_API_KEY','secret')
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status,json={'error':'secret'})), trust_env=False) as http:
            with pytest.raises(ServiceError) as error:
                await ModelClient(http).transcribe(b'audio','audio/wav','wav')
        assert error.value.status == expected
        assert 'secret' not in str(error.value)
    asyncio.run(check())


def test_speech_uses_official_proxy_and_validates_text(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY','secret')
    monkeypatch.setenv('LLM_TRANSCRIBE_MODEL','gpt-transcribe')
    monkeypatch.setenv('LLM_BASE_URL','https://proxy.test/v1')
    async def check():
        def response(request):
            assert str(request.url) == 'https://proxy.test/v1/audio/transcriptions'
            assert request.headers['Authorization'] == 'Bearer secret'
            assert b'gpt-transcribe' in request.content
            assert b'request.wav' in request.content
            return httpx.Response(200,json={'text':'  Сделай прохладнее.  '})
        async with httpx.AsyncClient(transport=httpx.MockTransport(response),trust_env=False) as http:
            assert await ModelClient(http).transcribe(b'audio','audio/wav','wav') == 'Сделай прохладнее.'
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200,json={'text':''})),trust_env=False) as http:
            with pytest.raises(ServiceError):
                await ModelClient(http).transcribe(b'audio','audio/wav','wav')
    asyncio.run(check())


def test_speech_failure_releases_upload_slot():
    with TestClient(app) as client:
        insert_session('guest')
        app.state.model.transcribe = AsyncMock(side_effect=[
            ServiceError('SPEECH_UNAVAILABLE', 'Недоступно', 503), 'Потеплее'])
        headers = {'Authorization':'Bearer guest','Content-Type':'audio/wav'}
        assert client.post('/api/v1/transcriptions',headers=headers,content=b'audio').status_code == 503
        assert client.post('/api/v1/transcriptions',headers=headers,content=b'audio').json() == {'text':'Потеплее'}
        assert not app.state.speech_lock.locked()
