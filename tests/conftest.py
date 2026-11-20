"""Все тесты используют поддельные ключи и транспорты в памяти."""

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    from scripts.offline_guard import block_network, FAKE_ENV
    for name, value in FAKE_ENV.items():
        monkeypatch.setenv(name, value)
    with block_network():
        yield
