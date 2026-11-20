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


@pytest.mark.parametrize(('mime','ext'), [
    ('audio/webm;codecs=opus','webm'), ('audio/mp4;codecs=mp4a.40.2','m4a'),
    ('audio/m4a','m4a'), ('audio/x-m4a','m4a'), ('audio/mpeg','mp3'),
    ('audio/mp3','mp3'), ('audio/wav','wav'), ('audio/x-wav','wav'),
    ('audio/ogg','ogg'), ('audio/flac','flac'), ('audio/x-flac','flac'),
])
def test_browser_mime_to_multipart(mime, ext):
    from email import policy
    from email.parser import BytesParser

    audio = b'\x00\xffrecording\r\n'
    def proxy(request):
        assert request.method == 'POST' and request.url.path == '/v1/audio/transcriptions'
        assert request.headers['authorization'] == 'Bearer offline-key'
        content_type = request.headers['content-type']
        envelope = BytesParser(policy=policy.default).parsebytes(
            f'Content-Type: {content_type}\r\n\r\n'.encode() + request.content)
        parts = {p.get_param('name', header='content-disposition'):p for p in envelope.iter_parts()}
        assert set(parts) == {'model','language','response_format','file'}
        assert [parts[k].get_content() for k in ('model','language','response_format')] == ['gpt-transcribe','ru','json']
        assert parts['file'].get_filename() == 'request.' + ext
        assert parts['file'].get_content_type() == mime.split(';')[0]
        assert parts['file'].get_payload(decode=True) == audio
        return httpx.Response(200,json={'text':'Теплее'})

    with TestClient(app) as client:
        insert_session('voice')
        app.state.model = ModelClient(httpx.AsyncClient(transport=httpx.MockTransport(proxy)))
        result = client.post('/api/v1/transcriptions',headers={'Authorization':'Bearer voice','Content-Type':mime},content=audio)
        assert result.status_code == 200 and result.json() == {'text':'Теплее'}


@pytest.mark.parametrize('extra', [0,1])
def test_file_size_boundary_streamed(extra):
    with TestClient(app) as client:
        insert_session('size')
        mock = AsyncMock(return_value='Текст')
        app.state.model.transcribe = mock
        def chunks():
            yield b'b' * 4_999_999
            yield b'b' * (1 + extra)
        response = client.post('/api/v1/transcriptions', headers={
            'Authorization':'Bearer size','Content-Type':'audio/webm'}, content=chunks())
        if extra:
            assert response.status_code == 413 and response.json()['code'] == 'AUDIO_TOO_LARGE'
            mock.assert_not_awaited()
        else:
            assert response.status_code == 200
            assert len(mock.await_args.args[0]) == 5_000_000


def test_shared_pacing_and_separate_stt_window(monkeypatch):
    from types import SimpleNamespace
    now = 0.
    async def delay(seconds):
        nonlocal now
        now += seconds

    starts = []
    def proxy(request):
        starts.append((now, request.url.path))
        if request.url.path.endswith('/transcriptions'):
            return httpx.Response(200, json={'text':'теплее'})
        return httpx.Response(200, json={'choices':[
            {'finish_reason':'stop','message':{'content':'{}'}}]})

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(proxy)) as http:
            client = ModelClient(http)
            monkeypatch.setattr('backend.clients.time', SimpleNamespace(monotonic=lambda:now))
            monkeypatch.setattr('backend.clients.asyncio', SimpleNamespace(sleep=delay))
            for _ in range(10):
                await client.transcribe(b'a','audio/wav','wav')
                await client.json('test', {})
            with pytest.raises(ServiceError) as caught:
                await client.transcribe(b'a','audio/wav','wav')
            assert caught.value.status == 429 and caught.value.code == 'SPEECH_LIMIT'
            assert len(starts) == 20
            for _ in range(10):
                await client.json('test', {})
            await client.transcribe(b'a','audio/wav','wav')
            assert len(starts) == 31
            for at, _ in starts:
                window = [path for t,path in starts if at-60 < t <= at]
                assert len(window) <= 30
                assert sum(p.endswith('/transcriptions') for p in window) <= 10

    asyncio.run(check())


@pytest.mark.parametrize(('status','code'), [(402,'SPEECH_BUDGET'),(413,'AUDIO_TOO_LARGE'),(429,'SPEECH_LIMIT')])
def test_proxy_voice_error_reaches_browser(status,code):
    with TestClient(app) as client:
        insert_session('error')
        app.state.model = ModelClient(httpx.AsyncClient(transport=httpx.MockTransport(
            lambda _:httpx.Response(status,json={'message':'hidden-budget-info'}))))
        response = client.post('/api/v1/transcriptions',headers={
            'Authorization':'Bearer error','Content-Type':'audio/webm'},content=b'a')
        assert response.status_code == status and response.json()['code'] == code
        assert 'hidden-budget-info' not in response.text
        assert app.state.model.calls == 1


def test_record_confirm_and_apply_through_simulator():
    from backend.clients import HackClient
    from backend.room import Room
    from tests.helpers import AT
    from tests.simulator import Simulator

    sim = Simulator()
    with TestClient(app) as browser:
        guest = insert_session('voice-session')
        transport = httpx.AsyncClient(transport=httpx.MockTransport(sim))
        guest.room = browser.portal.call(Room.create,HackClient('offline',transport),'stay_test','stay')
        app.state.model = ModelClient(httpx.AsyncClient(transport=httpx.MockTransport(
            lambda _:httpx.Response(200,json={'text':'Теплее'}))))
        headers = {'Authorization':'Bearer voice-session'}
        transcript = browser.post('/api/v1/transcriptions',headers={**headers,'Content-Type':'audio/webm'},content=b'recording')
        assert transcript.json() == {'text':'Теплее'} and sim.actions == 0
        command = dict(text=transcript.json()['text'],at=AT)
        headers['Idempotency-Key'] = 'voice-confirm-01'
        first = browser.post('/api/v1/messages',headers=headers,json=command)
        assert first.status_code == 200 and first.json()['reply']['response_class'] == 'done'
        assert browser.post('/api/v1/messages',headers=headers,json=command).json() == first.json()
        state = browser.get('/api/v1/state',headers=headers).json()['state']
        assert sim.actions == 1 and state['climate']['temperature_c'] == 24
        assert guest.solution.model.calls == 1
