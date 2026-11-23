#!/bin/bash
# SAIN Smart Room native macOS launcher: synthetic offline demo by default.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$ROOT"
export PYTHONUTF8=1
MODE="$(printenv SAIN_MODE || true)"
if [[ -z "$MODE" ]]; then MODE=offline; fi
if [[ "$MODE" != offline && "$MODE" != live ]]; then echo "SAIN_MODE must be offline or live" >&2; exit 2; fi
if [[ ! -f frontend/dist/index.html ]]; then echo "Missing prebuilt frontend/dist/index.html" >&2; exit 2; fi
if [[ "$MODE" == live ]]; then
  for name in LLM_API_KEY LLM_BASE_URL LLM_MODEL; do
    if [[ -z "$(printenv "$name" || true)" ]]; then echo "LIVE requires authorized $name set in this terminal" >&2; exit 2; fi
  done
fi
PY=""
for name in python3.11 python3.12 python3.13 python3.14 python3; do
  if command -v "$name" >/dev/null 2>&1 && "$name" -c 'import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
    PY="$(command -v "$name")"; break
  fi
done
if [[ -z "$PY" ]]; then echo "Python 3.11+ required" >&2; exit 2; fi
port_free() {
  "$PY" - "$1" <<'PYCODE'
import socket,sys
with socket.socket() as s:
    s.settimeout(.4)
    sys.exit(0 if s.connect_ex(('127.0.0.1',int(sys.argv[1]))) != 0 else 1)
PYCODE
}
for port in 8765 4173; do
  if ! port_free "$port"; then echo "Port $port busy; stop previous session first" >&2; exit 2; fi
done
if [[ ! -x .venv/bin/python ]]; then "$PY" -m venv .venv; fi
if ! .venv/bin/python -c 'import fastapi, uvicorn, httpx, jsonschema, pydantic' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r requirements.txt
fi
mkdir -p .runtime
chmod 700 .runtime
if [[ "$MODE" == live ]]; then module=scripts.live_client; frontendMode=live
else module=scripts.rehearse_client; frontendMode=rehearsal; fi
cleanup() { bash "$ROOT/STOP.command" >/dev/null 2>&1 || true; }
trap cleanup ERR
nohup "$ROOT/.venv/bin/python" -m "$module" >.runtime/backend.out 2>.runtime/backend.err </dev/null &
echo "$!" >.runtime/backend.pid
ready=0
for i in $(seq 1 60); do
  if "$PY" -c 'import urllib.request;urllib.request.urlopen("http://127.0.0.1:8765/health",timeout=1).read()' >/dev/null 2>&1; then ready=1; break; fi
  if ! kill -0 "$(cat .runtime/backend.pid)" 2>/dev/null; then break; fi
  sleep .5
done
if [[ "$ready" != 1 ]]; then echo "Backend failed: see .runtime/backend.err" >&2; false; fi
nohup "$ROOT/.venv/bin/python" "$ROOT/frontend/serve.py" --mode "$frontendMode" --port 4173 >.runtime/client.out 2>.runtime/client.err </dev/null &
echo "$!" >.runtime/client.pid
ready=0
for i in $(seq 1 30); do
  if "$PY" -c 'import urllib.request;urllib.request.urlopen("http://127.0.0.1:4173/",timeout=1).read()' >/dev/null 2>&1; then ready=1; break; fi
  if ! kill -0 "$(cat .runtime/client.pid)" 2>/dev/null; then break; fi
  sleep .5
done
if [[ "$ready" != 1 ]]; then echo "Frontend failed: see .runtime/client.err" >&2; false; fi
trap - ERR
echo "SAIN ($MODE) is running at http://127.0.0.1:4173"
echo "Local guest token: .venv/bin/python -m scripts.client_access dev --stay stay_test"
echo "Stop: bash STOP.command"
if [[ "$(printenv SAIN_CI || true)" != 1 && "$(printenv SAIN_NO_BROWSER || true)" != 1 ]]; then
  open http://127.0.0.1:4173 || true
fi
