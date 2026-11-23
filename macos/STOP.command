#!/bin/bash
# Terminate only process IDs of this local launcher; do not kill by port.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$ROOT"
if [[ ! -d .runtime ]]; then echo "SAIN not running"; exit 0; fi
for role in client backend; do
  path=".runtime/$role.pid"
  [[ -f "$path" ]] || continue
  pid="$(cat "$path")"
  rm -f "$path"
  if [[ ! "$pid" =~ ^[0-9]+$ ]] || ! kill -0 "$pid" 2>/dev/null; then continue; fi
  cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1 || true)"
  if [[ "$role" == client ]]; then
    [[ "$cmd" == *"frontend/serve.py"* ]] || { echo "Unowned PID $pid" >&2; continue; }
  else
    [[ "$cmd" == *"scripts.rehearse_client"* || "$cmd" == *"scripts.live_client"* ]] || { echo "Unowned PID $pid" >&2; continue; }
  fi
  if [[ "$cwd" != "$ROOT" ]]; then echo "Unowned cwd for PID $pid" >&2; continue; fi
  kill "$pid" 2>/dev/null || true
  echo "Stopped SAIN $role ($pid)"
done
