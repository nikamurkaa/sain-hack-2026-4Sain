"""Локальный транспорт комнат. Никакого сетевого сервера."""
import json
from copy import deepcopy

import httpx

from backend.core import default_state, moment
from tests.helpers import AT, WAKE, CATALOG, dataset


class Simulator:
    def __init__(self):
        self.closed = False
        self.until = WAKE
        self.data = dataset()
        self.sessions = {}
        self.runs = []
        self.actions = 0
        self.reads = 0
        self.auth = []
        self.persist_hook = None  # Synthetic loopback only; fsync before HTTP success.

    def __call__(self, request):
        self.auth.append(request.headers.get('Authorization'))
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        if path == '/case/2/getData' and request.method == 'GET':
            self.reads += 1
            return httpx.Response(200, json={'dataset':self.data, 'reference':{'never_pass_to_model':True}})
        if path == '/runs' and request.method == 'POST':
            if body != {'case':2}:
                return httpx.Response(400)
            run_id = 'test-run' if not self.runs else f'test-run-{len(self.runs)+1}'
            self.runs.append(run_id)
            if self.persist_hook is not None: self.persist_hook(self)
            return httpx.Response(201, json={'run_id':run_id})
        if path == '/room/session' and request.method == 'POST':
            rid = body['record_id']
            run_id = body.get('run_id')
            if run_id is not None and run_id not in self.runs:
                return httpx.Response(404)
            sid = f'{run_id}_session_{rid}' if run_id else f'session_{rid}'
            if sid not in self.sessions:
                initial = default_state(CATALOG['devices'])
                if body['kind'] == 'request':
                    record = next(r for r in self.data['requests'] if r['record_id'] == rid)
                    initial = deepcopy(record['initial_state'])
                session = {'session_id':sid,'kind':body['kind'],'record_id':rid,'initial_state':initial,'from':AT,'until':self.until}
                self.sessions[sid] = {'session':session,'entries':[]}
                if self.persist_hook is not None: self.persist_hook(self)
            return httpx.Response(201,json=self.sessions[sid]['session'])
        parts = path.split('/')
        if len(parts) != 4 or parts[2] not in self.sessions:
            return httpx.Response(404)
        saved = self.sessions[parts[2]]
        operation = parts[3]
        if operation == 'log' and request.method == 'GET':
            return httpx.Response(200, json=saved)
        if operation in ('action','scenario') and request.method == 'POST':
            if self.closed:
                return httpx.Response(409, json={'code':'ANSWER_SAVED'})
            steps = body['steps'] if operation == 'scenario' else [body]
            saved['entries'].append({'kind':operation, 'steps':steps})
            self.actions += int(operation == 'action')
            if self.persist_hook is not None: self.persist_hook(self)
            # Subprocess-only fault, after the synthetic action is fsynced.
            # No official/real provider is ever involved.
            import os
            if operation == "action" and os.getenv("SAIN_DEMO_CRASH_PROBE") == "after_post":
                os._exit(74)
            return httpx.Response(200, json={})
        if operation == 'state' and request.method == 'GET':
            at = moment(request.url.params['at'])
            current = deepcopy(saved['session']['initial_state'])
            steps = [step for entry in saved['entries'] for step in entry['steps']]
            for step in sorted(steps, key=lambda s:moment(s['at'])):
                if moment(step['at']) <= at:
                    current[step['device_id']].update(step['values'])
            return httpx.Response(200, json={'state':current})
        return httpx.Response(404)
