import asyncio
from copy import deepcopy
import hashlib
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from backend.clients import HackClient, ModelClient
from backend.core import ServiceError, default_state, moment
from backend.room import Room
from backend.runner import Solution, open_solution
from main import app, ClientSession
from tests.helpers import AT, WAKE, CATALOG, dataset, prefs, FakeModel, FakeRoom


class Simulator:
    def __init__(self):
        self.data=dataset(); self.sessions={};self.reads=0;self.auth=[];self.actions=0
    def __call__(self, request):
        self.auth.append(request.headers.get('Authorization'))
        path=request.url.path
        body=json.loads(request.content) if request.content else {}
        if path=='/case/2/getData':
            self.reads+=1
            return httpx.Response(200,json={'dataset':self.data,'reference':{'never_pass_to_model':True}})
        if path=='/runs':return httpx.Response(201,json={'run_id':'test-run'})
        if path=='/room/session':
            rid=body['record_id'];sid='session_'+rid
            if sid not in self.sessions:
                initial=default_state(CATALOG['devices'])
                session={'session_id':sid,'kind':body['kind'],'initial_state':initial,'from':AT,'until':WAKE}
                self.sessions[sid]={'session':session,'entries':[]}
            return httpx.Response(201,json=self.sessions[sid]['session'])
        sid=path.split('/')[2];saved=self.sessions[sid]
        if path.endswith('/log'):return httpx.Response(200,json=saved)
        if path.endswith('/scenario'):
            saved['entries'].append({'kind':'scenario','steps':body['steps']})
            return httpx.Response(200,json={})
        if path.endswith('/action'):
            self.actions+=1;saved['entries'].append({'kind':'action','steps':[body]})
            return httpx.Response(200,json={})
        if path.endswith('/state'):
            current=deepcopy(saved['session']['initial_state'])
            at=moment(request.url.params['at'])
            for e in saved['entries']:
                for s in e['steps']:
                    if moment(s['at'])<=at:current[s['device_id']].update(s['values'])
            return httpx.Response(200,json={'state':current})
        return httpx.Response(404,json={})


def test_complete_runner_fetches_once_and_forwards_token():
    async def run():
        sim=Simulator()
        async with httpx.AsyncClient(transport=httpx.MockTransport(sim),trust_env=False) as http:
            sol=await open_solution('evaluation-token','case2-dev-v1',http,FakeModel())
            assert sol.run_id is None and 'reference' not in sol.data
            answer=await sol.run()
            assert len(answer['stays'])==1 and len(answer['requests'])==1
            assert answer['requests'][0]['replies'][0]['response_class']=='done'
            assert sim.reads==1 and set(sim.auth)=={'Bearer evaluation-token'}
            assert sim.actions==1
            assert {x['session']['kind'] for x in sim.sessions.values()}=={'stay','request'}
    asyncio.run(run())


def test_team_token_creates_dev_run():
    async def run():
        sim=Simulator()
        async with httpx.AsyncClient(transport=httpx.MockTransport(sim),trust_env=False) as http:
            sol=await open_solution('team','case2-dev-v1',http,FakeModel(),'team')
            assert sol.run_id=='test-run'
    asyncio.run(run())


@pytest.mark.parametrize('applied',[True,False])
def test_uncertain_mutation_reconciled_without_retry(applied):
    async def run():
        calls=[]
        async def request(method,path,**kwargs):
            calls.append((method,path))
            if method=='POST':raise ServiceError('UPSTREAM_UNCERTAIN','unknown')
            return {'state':{'climate':{'temperature_c':22 if applied else 21}}}
        room=Room(SimpleNamespace(request=request),{'session_id':'s'})
        if applied:
            state=await room.execute([{'device_id':'climate','values':{'temperature_c':22},'at':AT}],AT)
            assert state['climate']['temperature_c']==22
        else:
            with pytest.raises(ServiceError,match='подтверждены'):await room.execute([{'device_id':'climate','values':{'temperature_c':22},'at':AT}],AT)
        assert sum(m=='POST' for m,p in calls)==1
    asyncio.run(run())


def test_partial_failure_is_not_done():
    async def run():
        count=0
        async def request(method,path,**kwargs):
            nonlocal count
            if method=='POST':
                count+=1
                if count==2:raise ServiceError('UPSTREAM_ERROR','second failed')
            return {'state':{'light':{'brightness':0},'sound':{'volume':20}}}
        room=Room(SimpleNamespace(request=request),{'session_id':'s'})
        with pytest.raises(ServiceError):await room.execute([{'device_id':'light','values':{'brightness':0},'at':AT},{'device_id':'sound','values':{'volume':0},'at':AT}],AT)
    asyncio.run(run())


def test_read_retries_and_no_secrets_in_error():
    async def run():
        count=0
        def handler(req):
            nonlocal count
            count+=1
            return httpx.Response(503 if count<3 else 200,json={'status':'ok'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler),trust_env=False) as http:
            with patch('backend.clients.asyncio.sleep',new=AsyncMock()):
                assert await HackClient('secret',http).request('GET','/health',retry=True)=={'status':'ok'}
        assert count==3
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(401,json={'code':'secret','message':'secret'})),trust_env=False) as http:
            with pytest.raises(ServiceError) as exc:await HackClient('secret',http).request('GET','/x')
            assert 'secret' not in str(exc.value) and 'secret' not in exc.value.code
    asyncio.run(run())


@pytest.mark.parametrize('finish,content',[('length','{}'),('stop','not json'),('stop','[]')])
def test_model_incomplete_json_rejected(monkeypatch,finish,content):
    monkeypatch.setenv('LLM_API_KEY','test');monkeypatch.setenv('LLM_MODEL','test-model')
    async def run():
        def response(req):return httpx.Response(200,json={'choices':[{'finish_reason':finish,'message':{'content':content}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(response),trust_env=False) as http:
            with pytest.raises(ServiceError):await ModelClient(http).json('test',{})
    asyncio.run(run())


def insert_session(token, room=None):
    room=room or FakeRoom()
    sol=Solution(dataset(),None,FakeModel())
    session=ClientSession(sol,room,prefs(),[],dataset()['stays'][0],time.monotonic()+1000,AT)
    app.state.sessions[hashlib.sha256(token.encode()).hexdigest()]=session
    return session


def test_http_auth_validation_and_health():
    with TestClient(app) as c:
        assert c.get('/health').json()['status']=='ok'
        assert c.post('/run',json={'case':2,'dataset_code':'case2-dev-v1'}).status_code==401
        assert c.post('/run',headers={'Authorization':'Bearer fake'},json={'case':1,'dataset_code':'x'}).status_code==422
        assert c.get('/api/v1/guest',headers={'Authorization':'Bearer unknown'}).status_code==401
        assert c.post('/api/v1/sessions',headers={'Authorization':'Bearer unknown'},json={'stay_id':'s'}).status_code==403


def test_client_isolation_and_idempotency():
    with TestClient(app) as c:
        a=insert_session('a');b=insert_session('b')
        headers={'Authorization':'Bearer a','Idempotency-Key':'message-001'}
        body={'text':'Теплее','at':AT}
        first=c.post('/api/v1/messages',headers=headers,json=body)
        assert first.status_code==200,first.text
        second=c.post('/api/v1/messages',headers=headers,json=body)
        assert first.json()==second.json() and a.room.executions==1 and b.room.executions==0
        assert c.post('/api/v1/messages',headers=headers,json=dict(body,text='Холоднее')).status_code==409
        assert c.get('/api/v1/state?at=2020-01-01T00:00:00%2B03:00',headers=headers).status_code==422
        assert c.delete('/api/v1/session',headers=headers).status_code==204
        assert c.get('/api/v1/guest',headers=headers).status_code==401


def test_run_http_cache_and_external_calls_once():
    sim=Simulator()
    with TestClient(app) as c:
        async def fake_open(token,code,http,model,team_token):
            client=httpx.AsyncClient(transport=httpx.MockTransport(sim),trust_env=False)
            # MockTransport не держит сетевые ресурсы.
            return await open_solution(token,code,client,FakeModel(),None)
        with patch('main.open_solution',side_effect=fake_open):
            headers={'Authorization':'Bearer eval'};body={'case':2,'dataset_code':'case2-dev-v1'}
            first=c.post('/run',headers=headers,json=body)
            assert first.status_code==200,first.text
            assert c.post('/run',headers=headers,json=body).json()==first.json()
            assert sim.reads==1


def test_failed_run_not_reexecuted():
    with TestClient(app) as c:
        fake=AsyncMock(side_effect=ServiceError('MODEL_UNAVAILABLE','Unavailable',503))
        with patch('main.open_solution',new=fake):
            for _ in range(2):
                response=c.post('/run',headers={'Authorization':'Bearer eval'},json={'case':2,'dataset_code':'case2-dev-v1'})
                assert response.status_code==503
            assert fake.await_count==1


def test_run_lock_does_not_block_health():
    async def check():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test',trust_env=False) as c:
                await app.state.run_lock.acquire()
                try:
                    assert (await c.get('/health')).status_code==200
                    r=await c.post('/run',headers={'Authorization':'Bearer eval'},json={'case':2,'dataset_code':'x'})
                    assert r.status_code==409
                finally:app.state.run_lock.release()
    asyncio.run(check())


def test_expired_session_does_not_read_upstream():
    with TestClient(app) as c:
        session=insert_session('expired');session.expires=0
        assert c.get('/api/v1/state',headers={'Authorization':'Bearer expired'}).status_code==401
        assert session.room.executions==0


def test_message_failure_same_key_never_runs_again():
    with TestClient(app) as c:
        session=insert_session('a')
        fake=AsyncMock(side_effect=ServiceError('ACTION_UNCONFIRMED','Unknown'))
        session.solution.message=fake
        headers={'Authorization':'Bearer a','Idempotency-Key':'failure-test'}
        for _ in range(2):
            assert c.post('/api/v1/messages',headers=headers,json={'text':'Теплее','at':AT}).status_code==502
        assert fake.await_count==1


def test_invalid_json_from_upstream_not_leaked():
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,text='secret')),trust_env=False) as http:
            with pytest.raises(ServiceError) as exc:await HackClient('secret',http).dataset('x')
            assert exc.value.code=='UPSTREAM_FORMAT' and 'secret' not in str(exc.value)
    asyncio.run(check())


def test_openapi_contains_client_response_contract():
    schema=app.openapi()
    assert schema['paths']['/api/v1/messages']['post']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/MessageResult')
    assert schema['paths']['/run']['post']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/RunAnswer')


@pytest.mark.parametrize('users,expected_peak', [(1,1),(4,3)])
def test_runner_parallelism_is_bounded_and_order_preserved(users, expected_peak):
    async def check():
        sim=Simulator();original=sim.data['requests'][0]
        sim.data['requests']=[dict(deepcopy(original),record_id='request_'+str(i),
                                   user_id='guest_'+str(i % users)) for i in range(8)]
        user = sim.data['users'][0]
        sim.data['users'].extend(dict(deepcopy(user), user_id='guest_'+str(i)) for i in range(users))
        async with httpx.AsyncClient(transport=httpx.MockTransport(sim),trust_env=False) as http:
            sol=await open_solution('eval','case2-dev-v1',http,FakeModel())
            active=0;peak=0;real=sol.message
            async def wrapped(*args,**kwargs):
                nonlocal active,peak
                active+=1;peak=max(peak,active)
                try:
                    await asyncio.sleep(0.01)
                    return await real(*args,**kwargs)
                finally:active-=1
            sol.message=wrapped
            result=await sol.run()
            assert peak==expected_peak
            assert [r['record_id'] for r in result['requests']]==['request_'+str(i) for i in range(8)]
    asyncio.run(check())

