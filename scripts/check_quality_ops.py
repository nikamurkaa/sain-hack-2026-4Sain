"""Isolated loopback-only cold-start and busy-port smoke; no external network."""
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    cmd = [sys.executable, str(ROOT / 'frontend' / 'serve.py'),
           '--mode', 'rehearsal', '--port', str(port)]
    first = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    challenger = None
    try:
        for _ in range(50):
            try:
                with urlopen('http://127.0.0.1:' + str(port) + '/', timeout=.5) as response:
                    assert response.status == 200
                    break
            except OSError:
                if first.poll() is not None:
                    raise RuntimeError('Cold start failed before health request')
                time.sleep(.06)
        else:
            raise AssertionError('Cold start never responded')
        challenger = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        assert challenger.wait(timeout=6) != 0, 'Occupied port accepted second server'
        with urlopen('http://127.0.0.1:' + str(port) + '/', timeout=1) as response:
            assert response.status == 200, 'Existing server failed after double bind'
    finally:
        if challenger is not None and challenger.poll() is None:
            challenger.terminate()
            challenger.wait(timeout=5)
        if first.poll() is None:
            first.terminate()
            first.wait(timeout=5)
    assert first.poll() is not None
    print('PASS: cold start, busy port refused, original server healthy, scoped shutdown')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
