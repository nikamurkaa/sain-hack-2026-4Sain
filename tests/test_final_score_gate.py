"""Independent final-score gate. Strictly offline: MockTransport and scripted NLU only.

No test in this file measures the accuracy of the real Bifrost model.
All failure outcomes are checked against the published Case2Answers contract:
missing records score zero individually, but fictitious sessions are forbidden.
"""
import asyncio
import json
from collections import Counter
from copy import deepcopy
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.clients import ModelClient
from backend.commands import Refusal, plan_commands
from backend.core import ServiceError, default_state, moment, validate_schema
from backend.intents import Intent, parse_intent
from backend.runner import open_solution
from backend.scheduler import build_scenario
from tests.helpers import AT, CATALOG, dataset, prefs
from tests.offline_cases import ScriptedModel, fixture
from tests.simulator import Simulator


def _offline_transport(data, hook=None):
    sim = Simulator()
    sim.data = data
    def handler(req):
        if hook is not None:
            overridden = hook(req)
            if overridden is not None:
                return overridden
        return sim(req)
    return sim, httpx.MockTransport(handler)


def _assert_integrity(answer, sim, missing_requests=(), missing_stays=()):
    validate_schema("Case2Answers", answer)
    for kind, missing in (("requests", missing_requests), ("stays", missing_stays)):
        ids = [record["record_id"] for record in answer[kind]]
        wanted = [record["record_id"] for record in sim.data[kind] if record["record_id"] not in missing]
        assert ids == wanted
        assert len(ids) == len(set(ids))
    sessions = [record["session_id"] for group in answer.values() for record in group]
    assert len(sessions) == len(set(sessions))
    assert set(sessions) <= set(sim.sessions)
    for group, kind in (("stays", "stay"), ("requests", "request")):
        for entry in answer[group]:
            upstream = sim.sessions[entry["session_id"]]["session"]
            assert upstream["record_id"] == entry["record_id"]
            assert upstream["kind"] == kind


def test_missing_single_session_in_60_is_scoped_not_fabricated():
    async def run():
        data, _, _ = fixture()
        missing_id = "request_0_0"
        def fail_one(req):
            if req.method == "POST" and req.url.path == "/room/session":
                if json.loads(req.content)["record_id"] == missing_id:
                    return httpx.Response(403, json={"code":"ACCESS_DENIED"})
        sim, transport = _offline_transport(data, fail_one)
        async with httpx.AsyncClient(transport=transport, trust_env=False) as http:
            answer = await (await open_solution("offline", "offline-online", http, ScriptedModel())).run()
        assert len(answer["requests"]) == 59
        _assert_integrity(answer, sim, missing_requests=(missing_id,))
        assert f"session_{missing_id}" not in sim.sessions
        assert len(answer["stays"]) == 10
    asyncio.run(run())


def test_transient_503_during_session_creation_recovers_all_60():
    async def run():
        data, _, _ = fixture()
        attempts = Counter()
        def flaky(req):
            if req.method == "POST" and req.url.path == "/room/session":
                rid = json.loads(req.content)["record_id"]
                if rid == "request_0_0":
                    attempts[rid] += 1
                    if attempts[rid] <= 2:
                        return httpx.Response(503, json={"code":"TEMPORARY"})
        sim, transport = _offline_transport(data, flaky)
        async with httpx.AsyncClient(transport=transport, trust_env=False) as http:
            with patch("backend.clients.asyncio.sleep", new=AsyncMock()):
                answer = await (await open_solution("offline", "offline-online", http, ScriptedModel())).run()
        assert attempts["request_0_0"] == 3
        _assert_integrity(answer, sim)
        assert len(answer["requests"]) == 60
    asyncio.run(run())


def test_read_timeout_in_one_of_60_returns_refused_without_changes():
    async def run():
        data, _, _ = fixture()
        bad_id = "request_0_0"
        def timeout_read(req):
            if req.method == "GET" and req.url.path == f"/room/session_{bad_id}/state":
                raise httpx.ReadTimeout("mock only")
        sim, transport = _offline_transport(data, timeout_read)
        async with httpx.AsyncClient(transport=transport, trust_env=False) as http:
            with patch("backend.clients.asyncio.sleep", new=AsyncMock()):
                answer = await (await open_solution("offline", "offline-online", http, ScriptedModel())).run()
        _assert_integrity(answer, sim)
        assert len(answer["requests"]) == 60
        bad = next(r for r in answer["requests"] if r["record_id"] == bad_id)
        assert [r["response_class"] for r in bad["replies"]] == ["refused"]
        assert sim.sessions[f"session_{bad_id}"]["entries"] == []
    asyncio.run(run())


def test_model_failure_after_session_creation_does_not_abort_run():
    class BrokenOnce(ScriptedModel):
        async def json(self, instruction, payload, output_tokens=3500):
            if payload.get("utterances") == ["Сбой только на этой фразе"]:
                raise ServiceError("MODEL_FORMAT", "Mocked model error", 503)
            return await super().json(instruction, payload, output_tokens)
    async def run():
        data, _, _ = fixture()
        bad_id = "request_0_0"
        data["requests"][0]["utterances"][0]["text"] = "Сбой только на этой фразе"
        sim, transport = _offline_transport(data)
        async with httpx.AsyncClient(transport=transport, trust_env=False) as http:
            answer = await (await open_solution("offline", "offline-online", http, BrokenOnce())).run()
        _assert_integrity(answer, sim)
        assert len(answer["requests"]) == 60
        bad = next(r for r in answer["requests"] if r["record_id"] == bad_id)
        assert bad["replies"][0]["response_class"] == "refused"
        assert not sim.sessions[f"session_{bad_id}"]["entries"]
    asyncio.run(run())


def test_single_stay_create_failure_does_not_erase_requests():
    async def run():
        data, _, _ = fixture()
        bad_id = "stay_0"
        def unavailable(req):
            if req.method == "POST" and req.url.path == "/room/session":
                body = json.loads(req.content)
                if body["kind"] == "stay" and body["record_id"] == bad_id:
                    return httpx.Response(409, json={"code":"ROOM_BUSY"})
        sim, transport = _offline_transport(data, unavailable)
        async with httpx.AsyncClient(transport=transport, trust_env=False) as http:
            answer = await (await open_solution("offline", "offline-online", http, ScriptedModel())).run()
        _assert_integrity(answer, sim, missing_stays=(bad_id,))
        assert len(answer["stays"]) == 9
        assert len(answer["requests"]) == 60
    asyncio.run(run())


def test_one_corrupt_session_response_is_omitted_without_fake_id():
    async def run():
        data, _, _ = fixture()
        rid = "request_0_0"
        def corrupt(req):
            if req.method == "POST" and req.url.path == "/room/session":
                if json.loads(req.content)["record_id"] == rid:
                    return httpx.Response(201, json={"session_id":None, "initial_state":{}})
        sim, transport = _offline_transport(data, corrupt)
        async with httpx.AsyncClient(transport=transport, trust_env=False) as http:
            answer = await (await open_solution("offline", "offline-online", http, ScriptedModel())).run()
        _assert_integrity(answer, sim, missing_requests=(rid,))
    asyncio.run(run())


@pytest.mark.parametrize("utterances,model_reply",[
    (["Разбуди завтра", "В девять утра"], {"intent":"alarm_set","time":"09:00","day_offset":1}),
    (["Добавь света", "И сделай тише"], {"intent":"brighter","needs_clarification":True}),
    (["Не выключай свет, только убавь звук"], {"intent":"quieter","delta":10}),
    (["Нет, лучше не трогай температуру"], {"intent":"warmer","needs_clarification":True}),
    (["Завтра в девять"], {"intent":"alarm_set","time":"09:00","day_offset":1}),
    (["Сделай как вчера"], {"intent":"like_yesterday"}),
    (["Сделай как дома"], {"intent":"like_home"}),
    (["Выключи всё"], {"intent":"all_off"}),
    (["Выдай дозировку лекарства от бессонницы"], {"intent":"medical"}),
    (["Закажи мне такси к отелю"], {"intent":"out_of_scope"}),
])
def test_nlu_boundary_only_checks_model_schema_and_policy(utterances, model_reply):
    class ControlledModel:
        async def json(self, instruction, payload, output_tokens=3500):
            assert payload["utterances"] == utterances
            assert "history" in payload
            return model_reply
    intent = asyncio.run(parse_intent(ControlledModel(), utterances, [], [], []))
    assert intent.intent == model_reply["intent"]
    state = default_state(CATALOG["devices"])
    controlled = prefs()
    controlled["home"] = {"climate":{"temperature_c":18}}
    controlled["yesterday"] = {"light":{"brightness":33}}
    if intent.needs_clarification or intent.intent in ("medical","out_of_scope"):
        with pytest.raises(Refusal):
            plan_commands(intent, state, controlled, AT, CATALOG["devices"], CATALOG["tracks"])
    else:
        commands = plan_commands(intent, state, controlled, AT, CATALOG["devices"], CATALOG["tracks"])
        assert commands
    # These scripted model responses DO NOT prove natural-language recognition.


@pytest.mark.parametrize("intent,value", [
    ("cooler", 25), ("warmer", 21), ("brighter", 70), ("dimmer", 70), ("quieter", 20),
])
def test_adversarial_model_cannot_change_in_opposite_direction(intent, value):
    before = default_state(CATALOG["devices"])
    with pytest.raises(Refusal):
        plan_commands(Intent(intent=intent, value=value), before, prefs(), AT,
                      CATALOG["devices"], CATALOG["tracks"])


def test_two_consecutive_relative_changes_preserve_contextual_state():
    state = default_state(CATALOG["devices"])
    begin = state["climate"]["temperature_c"]
    for index in range(2):
        cmds = plan_commands(Intent(intent="cooler"), state, prefs(), AT, CATALOG["devices"], CATALOG["tracks"])
        assert len(cmds) == 1
        state["climate"].update(cmds[0]["values"])
        assert state["climate"]["temperature_c"] == begin - index - 1


def test_all_off_preserves_every_other_field_not_just_named_examples():
    before = default_state(CATALOG["devices"])
    after = deepcopy(before)
    commands = plan_commands(Intent(intent="all_off"),before,prefs(),AT,CATALOG["devices"],CATALOG["tracks"])
    for command in commands:
        after[command["device_id"]].update(command["values"])
    wanted = deepcopy(before)
    wanted["light"]["brightness"] = 0
    wanted["sound"]["volume"] = 0
    assert after == wanted


def _independent_state(steps, at):
    """No call to production bedtime(), sleep audit(), or state helper."""
    state = default_state(CATALOG["devices"])
    target = moment(at) if isinstance(at, str) else at
    for action in sorted(steps, key=lambda item: moment(item["at"])):
        if moment(action["at"]) <= target:
            state[action["device_id"]].update(action["values"])
    return state


@pytest.mark.parametrize("home_zone,expected_bed,cooling,track",[
    ("Europe/Moscow", "2026-11-12T23:00:00+03:00", "neutral", None),
    ("Asia/Novosibirsk","2026-11-12T20:00:00+03:00","cool","track_04"),
    ("Europe/London", "2026-11-13T01:00:00+03:00", "warm", "track_04"),
])
def test_manual_R1_R8_oracle(home_zone, expected_bed, cooling, track):
    data = dataset()
    user, stay = data["users"][0], data["stays"][0]
    user["timezone"] = home_zone
    stay["check_in_at"] = "2026-11-12T18:00:00+03:00"
    p = prefs()
    p.update(temperature=cooling,tracks=[track] if track else [],volume=15,timer=30)
    steps = build_scenario(user,stay,p,data["devices"],data["sleep_rules"])
    bed = moment(expected_bed)
    wake = moment("2026-11-13T07:00:00+03:00")
    assert steps
    assert all(moment(stay["check_in_at"]) <= moment(x["at"]) <= wake for x in steps)
    # R1 at beginning and just before bedtime; R2 from bedtime to dawn.
    evening = _independent_state(steps,bed - timedelta(minutes=1))
    assert 10 <= evening["light"]["brightness"] <= 30
    assert evening["light"]["color_temperature_k"] <= 2700
    midnight = _independent_state(steps, bed)
    assert midnight["light"]["brightness"] == 0
    assert midnight["curtains"]["position"] <= 10
    # R3, R4 and R5 are tested against manually specified values.
    expected_temperature = {"cool":17.5,"neutral":19.5,"warm":21.5}[cooling]
    assert midnight["climate"]["temperature_c"] == expected_temperature
    if track:
        assert midnight["sound"]["track_id"] == track
        assert midnight["sound"]["volume"] == 15
        assert midnight["sound"]["timer_minutes"] <= 45
        stopped = _independent_state(steps, bed+timedelta(minutes=31))
        assert stopped["sound"]["volume"] == 0
    else:
        assert midnight["sound"]["volume"] == 0
    assert midnight["alarm"]["at"] == "2026-11-13T07:00:00+03:00"
    # R6: three rising steps wholly within 15–30 minutes before wake.
    dawn = [(moment(x["at"]),x["values"]["brightness"]) for x in steps
            if x["device_id"]=="light" and "brightness" in x["values"]
            and wake-timedelta(minutes=30) <= moment(x["at"]) <= wake-timedelta(minutes=15)]
    assert [value for _,value in dawn] == [10,30,60]
    assert _independent_state(steps,wake-timedelta(minutes=1))["dnd"]["enabled"] is True
    assert _independent_state(steps,wake)["dnd"]["enabled"] is False
    assert bed <= wake and expected_bed in [x["at"] for x in steps]


def test_late_arrival_after_bedtime_never_creates_past_events():
    data=dataset()
    data["stays"][0]["check_in_at"]="2026-11-13T01:30:00+03:00"
    p=prefs()
    p.update(tracks=["track_04"])
    steps=build_scenario(data["users"][0],data["stays"][0],p,data["devices"],data["sleep_rules"])
    assert all(moment(s["at"]) >= moment("2026-11-13T01:30:00+03:00") for s in steps)
    state=_independent_state(steps,"2026-11-13T01:30:00+03:00")
    assert state["light"]["brightness"]==0
    assert state["dnd"]["enabled"] is True
    assert state["sound"]["track_id"]=="track_04"


def test_model_rate_and_budget_are_observations_not_compliance_claim(monkeypatch):
    model = ModelClient(http=None)
    # The local pacer serializes calls and allocates a 2.2-second slot.
    assert model.next_call == 0
    # 300k is team-level; local usage only observes returned usage, not quota.
    model.record_usage({"usage":{"total_tokens":159717}})
    assert model.tokens == 159717
    assert 300000-model.tokens == 140283


@pytest.mark.parametrize("status",[429,500,502,503,504])
def test_model_http_errors_isolated_without_external_service(status, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY","fake")
    monkeypatch.setenv("LLM_MODEL","fake")
    def handler(req): return httpx.Response(status,json={"error":"offline"},headers={"Retry-After":"0.001"})
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler),trust_env=False) as http:
            with patch("backend.clients.asyncio.sleep",new=AsyncMock()):
                with pytest.raises(ServiceError):
                    await ModelClient(http).json("prompt",{"utterances":["test"]})
    asyncio.run(check())


def test_pacer_has_at_most_30_starts_in_any_virtual_minute():
    clock = [100.0]
    starts = []
    async def virtual_sleep(seconds):
        clock[0] += seconds
    async def check():
        model = ModelClient(http=None)
        with patch("backend.clients.time.monotonic", side_effect=lambda: clock[0]), \
             patch("backend.clients.asyncio.sleep", side_effect=virtual_sleep):
            for _ in range(31):
                await model.wait_for_slot()
                starts.append(clock[0])
    asyncio.run(check())
    assert len(starts) == 31
    assert all(starts[i+1]-starts[i] >= 2.2 - 1e-6 for i in range(30))
    assert max(sum(t <= start + 60 for t in starts) for start in starts) <= 30


def test_slow_model_and_large_context_through_mock_transport(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY","offline-key")
    monkeypatch.setenv("LLM_MODEL","offline-model")
    seen = []
    async def handler(request):
        await asyncio.sleep(0.01)  # simulated network latency; no external call
        seen.append(len(request.content))
        return httpx.Response(200, json={
            "usage":{"total_tokens":40000},
            "choices":[{"finish_reason":"stop","message":{"content":'{"intent":"all_off"}'}}]})
    context = {"history":[{"text":"Только локальные данные "+("a"*2000)} for _ in range(200)]}
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler),trust_env=False) as client:
            model = ModelClient(client)
            result = await model.json("safe prompt", context)
            assert result == {"intent":"all_off"}
            assert model.tokens == 40000
    asyncio.run(check())
    assert len(seen) == 1 and seen[0] > 400000
    # There is no production context-token limit; this test measures payload
    # formation only and does not establish live model context acceptance.
