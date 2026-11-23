#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$ROOT"
uname -sm
for p in python3.11 python3.12 python3.13 python3.14 python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
    "$p" --version
    [[ -f frontend/dist/index.html ]] && echo "Frontend build: present" || echo "Frontend build: MISSING"
    exit 0
  fi
done
echo "Python 3.11+ is missing" >&2
exit 2
