import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.commands import plan_commands
from backend.intents import parse_intent
from main import app
from tests.helpers import AT, CATALOG, prefs
from backend.core import default_state


@pytest.mark.parametrize('before,after', [(19, 18), (16, 16)])
def test_dictated_cooler_changes_only_climate(before, after):
    intent = asyncio.run(parse_intent(None, ['Сделай попрохладнее.'], [], []))
    state = default_state(CATALOG['devices'])
    state['climate']['temperature_c'] = before
    commands = plan_commands(intent, state, prefs(), AT, CATALOG['devices'], CATALOG['tracks'])
    assert commands == [{'device_id':'climate','values':{'temperature_c':after},'at':AT}]


def test_voice_page_assets_are_served():
    with TestClient(app) as client:
        for path in ['/voice/', '/voice/chat.mjs', '/voice/dictation.mjs']:
            assert client.get(path).status_code == 200
