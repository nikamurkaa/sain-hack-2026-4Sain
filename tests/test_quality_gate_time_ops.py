"""Synthetic operational/timezone gates; no requests to organizer infrastructure."""
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import subprocess
import sys
import time

from fastapi.testclient import TestClient
from backend.core import moment
from scripts.rehearse_client import build_rehearsal
from main import app as core

ROOT = Path(__file__).resolve().parents[1]


def test_dst_spring_fall_instants_and_midnight_are_offset_aware():
    berlin = ZoneInfo('Europe/Berlin')
    samples = [
        ('2026-03-29T01:50:00+01:00', '2026-03-29T03:10:00+02:00', 20),
        ('2026-10-25T02:50:00+02:00', '2026-10-25T02:10:00+01:00', 20),
        ('2026-11-12T23:59:00+03:00', '2026-11-13T00:01:00+03:00', 2),
    ]
    for beginning, ending, expected_minutes in samples:
        left, right = moment(beginning), moment(ending)
        assert (right - left) == timedelta(minutes=expected_minutes)
        assert left.isoformat() == beginning
        assert right.isoformat() == ending
        if left.year == 2026 and left.month in (3, 10):
            assert left.astimezone(berlin).utcoffset() is not None
            assert right.astimezone(berlin).utcoffset() is not None


def test_expired_guest_token_is_denied_without_replacing_access_control():
    with TestClient(build_rehearsal()) as client:
        response = client.post('/api/v1/sessions', headers={'Authorization':'Bearer offline-team'},
                               json={'source':'dev','stay_id':'stay_test'})
        assert response.status_code == 201, response.text
        token = response.json()['session_token']
        hashed = hashlib.sha256(token.encode()).hexdigest()
        session = core.state.sessions[hashed]
        session.expires = time.monotonic() - 1
        auth = {'Authorization':'Bearer '+token}
        assert client.get('/api/v1/session',headers=auth).status_code == 401
        assert client.get('/api/v1/guest',headers=auth).status_code == 401
        assert client.get('/api/v1/state',headers=auth).status_code == 401


def test_offline_frontend_can_cold_start_and_reject_double_bind():
    # pytest enforces socket isolation in the parent; subprocess confines
    # its network access to 127.0.0.1 on an ephemeral port.
    result = subprocess.run([sys.executable, '-m', 'scripts.check_quality_ops'],
                            cwd=ROOT, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr + result.stdout
    assert 'PASS: cold start' in result.stdout


def test_windows_scripts_define_owned_process_shutdown_and_mode_guards():
    launcher=(ROOT/'launcher.ps1').read_text(encoding='utf-8')
    stop=(ROOT/'stop.ps1').read_text(encoding='utf-8')
    assert 'Open-Port 4173' in launcher and 'Open-Port 8765' in launcher
    assert 'REHEARSAL' in launcher and 'STAND' in launcher
    assert 'owned-pids.json' in launcher and 'owned-pids.json' in stop
    assert 'Win32_Process' in stop and 'ProcessId' in stop
    assert 'Stop-Process' in stop and 'CommandLine' in stop
    assert 'scripts.rehearse_client' in stop
    # No machine-wide process termination, no embedded production credentials.
    assert 'taskkill /f /im' not in stop.lower()
    assert 'hack_team_token=' not in launcher.lower()
