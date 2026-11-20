"""Блокировка IP-соединений для локальной проверки Python."""
from contextlib import contextmanager
import socket
from unittest.mock import patch

FAKE_ENV = {
    'HACK_API_URL': 'https://simulator.invalid',
    'HACK_TEAM_TOKEN': 'offline-team',
    'LLM_BASE_URL': 'https://model.invalid/v1',
    'LLM_MODEL': 'offline-model',
    'LLM_API_KEY': 'offline-key',
}


@contextmanager
def block_network():
    def deny(*args, **kwargs):
        raise RuntimeError('Network disabled for offline checks')

    with patch.object(socket.socket, 'connect', deny), patch.object(socket.socket, 'connect_ex', deny), patch.object(socket, 'getaddrinfo', deny):
        yield
