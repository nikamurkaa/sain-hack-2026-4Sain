"""Stage 2 independent *structured-action* oracle, NOT a language-model score.

Utterance labels are documentation of intended semantics: the test feeds parsed
Intent objects, never pretends a scripted FakeLLM understood unseen Russian.
Each case asserts every unchanged field as well as the requested device changes.
"""
from copy import deepcopy
import pytest

from backend.commands import Refusal, plan_commands
from backend.intents import Intent
from backend.core import default_state
from tests.helpers import AT, WAKE, CATALOG, prefs


# case id, sample utterance, *structured* model output, expected changes or None
# None means refusal with NO simulator state mutation.
OFFICIAL_19 = [
    ("brighter", "Сделай лампы поярче", {"intent":"brighter"}, {"light":{"brightness":90}}),
    ("dimmer", "Приглуши освещение", {"intent":"dimmer"}, {"light":{"brightness":50}}),
    ("warmer", "Здесь зябко", {"intent":"warmer"}, {"climate":{"temperature_c":24}}),
    ("cooler", "Снизь температуру в номере", {"intent":"cooler"}, {"climate":{"temperature_c":22}}),
    ("all_off", "Погаси всё", {"intent":"all_off"}, {"light":{"brightness":0},"sound":{"volume":0}}),
    ("sound_on", "Пусть играет дождь", {"intent":"sound_on","track_id":"track_04"}, {"sound":{"track_id":"track_04","volume":30}}),
    ("quieter", "Музыка слишком громкая", {"intent":"quieter"}, {"sound":{"volume":10}}),
    ("curtains", "Задёрни занавески", {"intent":"curtains","value":0}, {"curtains":{"position":0}}),
    ("alarm_set", "Разбудите в шесть тридцать", {"intent":"alarm_set","time":"06:30"}, {"alarm":{"at":"2026-11-13T06:30:00+03:00"}}),
    ("alarm_shift", "Перенеси подъём на полчаса позже", {"intent":"alarm_shift","delta":30}, {"alarm":{"at":"2026-11-13T07:30:00+03:00"}}),
    ("alarm_cancel", "Снимите будильник", {"intent":"alarm_cancel"}, {"alarm":{"at":None}}),
    ("going_to_bed", "Отправляюсь спать", {"intent":"going_to_bed"}, {"light":{"brightness":0},"curtains":{"position":0},"dnd":{"enabled":True},"climate":{"temperature_c":19.5},"sound":{"volume":0}}),
    ("woke_up", "Я уже встал", {"intent":"woke_up"}, {"light":{"brightness":70,"color_temperature_k":4000},"alarm":{"at":None},"dnd":{"enabled":False}}),
    ("like_yesterday", "Повтори вчерашние настройки", {"intent":"like_yesterday"}, {"light":{"brightness":33}}),
    ("do_not_disturb", "Без звонков и уборки", {"intent":"do_not_disturb"}, {"dnd":{"enabled":True}}),
    ("like_home", "Настрой как у меня дома", {"intent":"like_home"}, {"climate":{"temperature_c":18}}),
    ("out_of_scope", "Вызови такси", {"intent":"out_of_scope"}, None),
    ("invalid_value", "Установи 35 градусов", {"intent":"warmer","value":35}, None),
    ("medical", "Какие таблетки выпить для сна?", {"intent":"medical"}, None),
]


def planned_effect(raw, initial, personal=None):
    personal = deepcopy(personal or prefs())
    try:
        commands = plan_commands(Intent.model_validate(raw), deepcopy(initial), personal,
                                 AT, CATALOG["devices"], CATALOG["tracks"])
    except Refusal:
        return None, deepcopy(initial)
    actual = deepcopy(initial)
    for command in commands:
        actual[command["device_id"]].update(command["values"])
    return commands, actual


@pytest.mark.parametrize("name,phrase,raw,delta", OFFICIAL_19, ids=[row[0] for row in OFFICIAL_19])
def test_full_state_contract_for_19_official_categories(name, phrase, raw, delta):
    initial = default_state(CATALOG["devices"])
    initial["alarm"]["at"] = WAKE
    personal = prefs()
    personal["tracks"] = ["track_04"] if name == "sound_on" else []
    personal["home"] = {"climate":{"temperature_c":18}}
    personal["yesterday"] = {"light":{"brightness":33}}
    before = deepcopy(initial)
    commands, result = planned_effect(raw, initial, personal)
    expected = deepcopy(before)
    if delta is None:
        assert commands is None, (name, phrase)
    else:
        assert commands is not None and len(commands) == len(delta), (name, phrase)
        for device, changes in delta.items():
            expected[device].update(changes)
    assert result == expected, (name, phrase)
    assert initial == before, "The planner must not mutate the incoming snapshot"


@pytest.mark.parametrize("raw,reason", [
    ({"intent":"alarm_set","needs_clarification":True}, "missing_alarm_time"),
    ({"intent":"like_home","needs_clarification":True}, "ambiguous_home"),
    ({"intent":"brighter","needs_clarification":True}, "competing_actions"),
    ({"intent":"curtains","value":150}, "curtain_upper_bound"),
    ({"intent":"cooler","value":35}, "temperature_upper_bound"),
    ({"intent":"quieter","value":-5}, "volume_lower_bound"),
    ({"intent":"alarm_set","time":None}, "unknown_wake_time"),
    ({"intent":"invalid_value"}, "unsupported_value"),
    ({"intent":"medical"}, "unsafe_medical"),
    ({"intent":"out_of_scope"}, "non_room_action"),
])
def test_negative_ambiguous_conflicting_and_invalid_actions_do_not_mutate(raw, reason):
    initial = default_state(CATALOG["devices"])
    before = deepcopy(initial)
    commands, result = planned_effect(raw, initial)
    assert commands is None, reason
    assert result == before and initial == before, reason


@pytest.mark.parametrize("raw,expected", [
    ({"intent":"warmer","delta":2}, 25),
    ({"intent":"cooler","delta":2}, 21),
    ({"intent":"brighter","delta":10}, 80),
    ({"intent":"dimmer","delta":10}, 60),
    ({"intent":"quieter","delta":5}, 15),
])
def test_explicit_deltas_preserve_every_other_field(raw, expected):
    initial = default_state(CATALOG["devices"])
    commands, result = planned_effect(raw, initial)
    assert commands is not None
    target = {"warmer":("climate","temperature_c"), "cooler":("climate","temperature_c"),
              "brighter":("light","brightness"), "dimmer":("light","brightness"),
              "quieter":("sound","volume")}[raw["intent"]]
    oracle = deepcopy(initial)
    oracle[target[0]][target[1]] = expected
    assert result == oracle


def test_unexpected_sequence_reconciles_result_not_old_snapshot():
    initial = default_state(CATALOG["devices"])
    current = deepcopy(initial)
    for raw in ({"intent":"cooler"}, {"intent":"cooler"}, {"intent":"warmer"},
                {"intent":"all_off"}, {"intent":"brighter"}):
        commands, current = planned_effect(raw, current)
        assert commands is not None
    assert current["climate"]["temperature_c"] == 22
    assert current["light"]["brightness"] == 20
    assert current["sound"]["volume"] == 0
    assert current["curtains"] == initial["curtains"]
    assert current["alarm"] == initial["alarm"]
    assert current["dnd"] == initial["dnd"]
