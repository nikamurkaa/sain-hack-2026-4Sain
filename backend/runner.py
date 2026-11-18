"""Общий сервис для проверки и пользовательского интерфейса."""
import asyncio
from datetime import timedelta

from backend.clients import HackClient
from backend.commands import Refusal, plan_commands, success_text
from backend.core import ServiceError, moment, validate_schema
from backend.intents import parse_intent
from backend.preferences import PreferenceResolver
from backend.room import Room
from backend.scheduler import build_scenario


class Solution:
    def __init__(self, data, client, model, run_id=None):
        self.data, self.client, self.model, self.run_id = data, client, model, run_id
        self.preferences = PreferenceResolver(data, model)

    def user(self, user_id):
        return next(u for u in self.data['users'] if u['user_id'] == user_id)

    def stay(self, stay_id):
        return next(s for s in self.data['stays'] if s['record_id'] == stay_id)

    async def prefs(self, user_id, at):
        # «Вчера» относится к местному времени текущего проживания.
        previous_date = (moment(at).date() - timedelta(days=1)).isoformat()
        return await self.preferences.resolve(user_id, at, previous_date)

    async def prepare(self, stay):
        prefs = await self.prefs(stay['user_id'], stay['check_in_at'])
        steps = build_scenario(self.user(stay['user_id']), stay, prefs, self.data['devices'], self.data['sleep_rules'])
        room = await Room.create(self.client, stay['record_id'], 'stay', self.run_id)
        await room.scenario(steps)
        return room, prefs, steps

    async def message(self, room, user_id, texts, at, base_state=None):
        try:
            prefs = await self.prefs(user_id, at)
            intent = await parse_intent(self.model, texts, self.data['intents'], self.data['tracks'])
            state = base_state if base_state is not None else await room.state(at)
            commands = plan_commands(intent, state, prefs, at, self.data['devices'], self.data['tracks'])
        except Refusal as exc:
            return {'role': 'agent', 'at': at, 'text': str(exc), 'response_class': 'refused'}, await room.state(at)
        state = await room.execute(commands, at)
        return {'role': 'agent', 'at': at, 'text': success_text(commands), 'response_class': 'done'}, state

    async def run(self):
        async def bounded_map(items, operation):
            semaphore = asyncio.Semaphore(3)
            async def work(item):
                async with semaphore:
                    return await operation(item)
            tasks = [asyncio.create_task(work(item)) for item in items]
            try:
                return await asyncio.gather(*tasks)
            except BaseException:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise

        async def prepare_stay(stay):
            room, _, _ = await self.prepare(stay)
            return {'record_id': stay['record_id'], 'session_id': room.session['session_id']}

        async def handle_request(request):
            room = await Room.create(self.client, request['record_id'], 'request', self.run_id)
            texts = [u['text'] for u in sorted(request['utterances'], key=lambda u: moment(u['at']))
                     if u['role'] == 'user' and moment(u['at']) <= moment(request['at'])]
            reply, _ = await self.message(room, request['user_id'], texts, request['at'], room.session['initial_state'])
            return {'record_id': request['record_id'], 'session_id': room.session['session_id'], 'replies': [reply]}

        answer = {'stays': await bounded_map(self.data['stays'], prepare_stay),
                  'requests': await bounded_map(self.data['requests'], handle_request)}
        validate_schema('Case2Answers', answer)
        return answer


async def open_solution(token, code, http, model, team_token=None):
    client = HackClient(token, http)
    data = await client.dataset(code)
    run_id = None
    if team_token and token == team_token:
        if data['meta']['phase'] != 'dev':
            raise ServiceError('DEV_ONLY', 'Командный токен используется только для dev-прогона.', 403)
        run = await client.dev_run()
        run_id = run['run_id']
    return Solution(data, client, model, run_id)
