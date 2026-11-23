"""Offline audit of *reachable Git history* without printing secret bytes.

Never rewrites refs or histories. A suspicious path/blob blocks release until
the owner reviews and rotates exposed credentials. Only regex-like obvious
credentials are detectable; this is not an exhaustive forensic audit.
"""
import re
import subprocess

SUSPECT_PATH = re.compile(
    r"(?i)(?:^|/)(?:\.env(?:\.[^/]+)?|llm\.key|id_(?:rsa|ed25519)(?:\.pub)?|"
    r"[^/]+\.(?:pem|p12|pfx|ppk|key)|team25(?:\([^/]*\))?\.zip)$"
)
SUSPECT_TEXT = re.compile(
    rb"(?:sk-[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{36,}|"
    rb"github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
MAX_BLOB = 2_000_000


def git(*args, input=None):
    return subprocess.run(["git", *args], input=input, capture_output=True, check=True).stdout


def check():
    shallow = git("rev-parse", "--is-shallow-repository").strip()
    if shallow != b"false":
        raise RuntimeError("Refusing to certify incomplete shallow Git history")
    records = git("rev-list", "--objects", "--all").splitlines()
    if not records:
        raise RuntimeError("No Git objects available for audit")
    objects = {}
    for line in records:
        sha, _, path = line.partition(b" ")
        if len(sha) != 40:
            continue
        obj = objects.setdefault(sha.decode("ascii"), [])
        if path:
            obj.append(path.decode("utf-8", "replace"))
    checks = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                 input="".join(oid + "\n" for oid in objects).encode()).splitlines()
    suspect = set()
    scanned = 0
    skipped_large = 0
    for row in checks:
        fields = row.decode().split()
        if len(fields) != 3 or fields[1] != "blob":
            continue
        oid, _, size_str = fields
        size = int(size_str)
        paths = objects[oid]
        if any(path != ".env.example" and SUSPECT_PATH.search(path) for path in paths):
            suspect.add(oid[:12])
        if size > MAX_BLOB:
            skipped_large += 1
            continue
        blob = git("cat-file", "blob", oid)
        if b"\0" in blob[:4096]:
            continue
        scanned += 1
        if SUSPECT_TEXT.search(blob):
            suspect.add(oid[:12])
    print(f"Git history audit: reachable={len(objects)}, scanned_text_blobs={scanned}, "
          f"large_skipped={skipped_large}, suspicious_objects={len(suspect)}")
    if suspect:
        print("Suspicious Git object ID prefixes only (NOT secret values): "
              + ", ".join(sorted(suspect)[:20]))
        raise SystemExit(1)


if __name__ == "__main__":
    check()
