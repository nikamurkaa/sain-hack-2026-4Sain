"""Общий сервис для проверки и пользовательского интерфейса."""
import asyncio
import logging
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
        self.prepared = {}

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
        if self.data['meta']['phase'] == 'final':
            self.prepared[stay['record_id']] = (room, prefs, steps)
        return room, prefs, steps

    async def message(self, room, user_id, texts, at, base_state=None, history=None):
        try:
            intent = await parse_intent(self.model, texts, self.data['intents'], self.data['tracks'], history)
            prefs = {}
            if intent.intent in ('going_to_bed', 'woke_up', 'like_home', 'like_yesterday', 'sound_on'):
                prefs = await self.prefs(user_id, at)
            state = base_state if base_state is not None else await room.state(at)
            hotel_zone = next((s.get("hotel_timezone") for s in self.data["stays"]
                               if s["user_id"] == user_id), None)
            commands = plan_commands(intent, state, prefs, at, self.data['devices'], self.data['tracks'],
                                     hotel_timezone=hotel_zone)
        except Refusal as exc:
            return {'role': 'agent', 'at': at, 'text': str(exc), 'response_class': 'refused'}, await room.state(at)
        state = await room.execute(commands, at)
        return {'role': 'agent', 'at': at, 'text': success_text(commands, self.data['tracks']), 'response_class': 'done'}, state

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
            try:
                room, _, _ = await self.prepare(stay)
            except Exception:
                # An individual malformed stay cannot invalidate the whole /run.
                # No fictitious session ID or successful scenario is returned.
                # Без подтверждённого сценария запись нельзя считать выполненной.
                logging.getLogger(__name__).warning('Не удалось подготовить один заезд')
                return None
            return {'record_id': stay['record_id'], 'session_id': room.session['session_id']}

        async def handle_user(requests):
            history = []
            answers = []
            for request in sorted(requests, key=lambda item: moment(item['at'])):
                texts = [u['text'] for u in sorted(request['utterances'], key=lambda u: moment(u['at']))
                         if u['role'] == 'user' and moment(u['at']) <= moment(request['at'])]
                try:
                    room = await Room.create(self.client, request['record_id'], 'request', self.run_id)
                except Exception:
                    logging.getLogger(__name__).warning('Не удалось создать сеанс одной просьбы')
                    history.append({'at': request['at'], 'utterances': texts,
                                    'reply': {'role': 'agent', 'at': request['at'], 'response_class': 'refused',
                                              'text': 'Не удалось открыть сеанс номера.'}})
                    continue
                try:
                    reply, _ = await self.message(room, request['user_id'], texts, request['at'],
                                                 room.session['initial_state'], history=history)
                except Exception:
                    reply = {'role': 'agent', 'at': request['at'], 'response_class': 'refused',
                             'text': 'Не удалось подтвердить выполнение просьбы. Проверьте состояние номера.'}
                history.append({'at': request['at'], 'utterances': texts, 'reply': reply})
                answers.append({'record_id': request['record_id'],
                                'session_id': room.session['session_id'], 'replies': [reply]})
            return answers

        # Параллельность остаётся между пользователями. Их разговоры изолированы.
        conversations = {}
        for request in self.data['requests']:
            conversations.setdefault(request['user_id'], []).append(request)
        stays = await bounded_map(self.data['stays'], prepare_stay)
        groups = await bounded_map(conversations.values(), handle_user)
        answers = {item['record_id']: item for group in groups for item in group}
        answer = {'stays': [item for item in stays if item is not None],
                  'requests': [answers[item['record_id']] for item in self.data['requests']
                               if item['record_id'] in answers]}
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
        run_id = run.get('run_id')
        if not isinstance(run_id, str) or not run_id:
            raise ServiceError('UPSTREAM_FORMAT', 'Отсутствует идентификатор dev-прогона.')
    return Solution(data, client, model, run_id)

