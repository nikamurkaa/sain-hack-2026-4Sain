"""Fail-closed Stage 1 tracked-file secrets check; never print secret values.

This checks only the *current tracked tree*, not past Git blobs, runner
secrets, local developer files or external materials. No network access.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_FILE = re.compile(
    r"(?i)(?:^|/)(?:\.env(?:\.[^/]+)?|id_(?:rsa|ed25519)(?:\.pub)?|[^/]+\.(?:pem|p12|pfx|ppk|key)|team25(?:\([^/]*\))?\.zip)$"
)
SECRET_TEXT = re.compile(
    rb"(?:sk-[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}"
    rb"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


def tracked_files():
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [Path(p.decode("utf-8")) for p in paths.split(b"\0") if p]


def scan():
    suspicious = []
    text_count = 0
    for path in tracked_files():
        name = path.as_posix()
        if name != ".env.example" and SENSITIVE_FILE.search(name):
            suspicious.append(name)
            continue
        full = ROOT / path
        if not full.is_file() or full.is_symlink():
            continue
        # Bounded textual scan; binary assets cannot be meaningfully scanned
        # with a regex, so this is not a raw history/bytes audit.
        if full.stat().st_size > 2_000_000:
            continue
        raw = full.read_bytes()
        if b"\0" in raw[:4096]:
            continue
        text_count += 1
        if SECRET_TEXT.search(raw):
            suspicious.append(name)
    print(f"Stage1 tracked-file gate: checked_text_files={text_count}; findings={len(suspicious)}")
    if suspicious:
        # Files only: never output matching bytes or credential values.
        print("Flagged tracked paths: " + ", ".join(sorted(set(suspicious))[:30]))
        raise SystemExit(1)


if __name__ == "__main__":
    scan()
