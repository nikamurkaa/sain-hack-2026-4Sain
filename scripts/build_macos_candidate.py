"""Deterministic macOS demo ZIP with SHA-256 manifest; no secrets or official data."""
import hashlib
import os
from pathlib import Path
import subprocess
import zipfile
from scripts.build_windows_candidate import ROOT, tracked

NAME = "SAIN-Smart-Room-macOS.zip"
ALIASES = {
    "macos/START.command": "START.command",
    "macos/STOP.command": "STOP.command",
    "macos/CHECK_ENV.command": "CHECK_ENV.command",
    "macos/README_MACOS.md": "README_MACOS.md",
}
REQUIRED = {"START.command", "STOP.command", "CHECK_ENV.command", "README_MACOS.md",
            "BUILD_INFO.txt", "SHA256SUMS.txt", "frontend/dist/index.html",
            "frontend/serve.py", "main.py", "requirements.txt", "scripts/rehearse_client.py"}

def build():
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if os.getenv("SAIN_SOURCE_SHA", sha) != sha:
        raise RuntimeError("Source SHA mismatch")
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError("Missing Vite build")
    content = {}
    for path in tracked():
        source = path.as_posix()
        if path.parts[0] in (".github", "windows"):
            continue
        if source.startswith("macos/") and source not in ALIASES:
            continue
        content[ALIASES.get(source, source)] = (ROOT / path).read_bytes()
    for f in sorted((ROOT / "frontend/dist").rglob("*")):
        if f.is_file() and not f.is_symlink():
            content[f.relative_to(ROOT).as_posix()] = f.read_bytes()
    content["BUILD_INFO.txt"] = (
        f"SAIN Smart Room / 4Sain / macOS offline demo\nSource SHA: {sha}\n"
        "Offline: synthetic simulator; LIVE provider NOT TESTED by packaging.\n"
        "Check native macOS smoke separately at this exact commit SHA.\n"
    ).encode("utf-8")
    sums = {name: hashlib.sha256(blob).hexdigest() for name, blob in sorted(content.items())}
    content["SHA256SUMS.txt"] = "".join(f"{digest}  {name}\n" for name, digest in sums.items()).encode()
    missing = REQUIRED - content.keys()
    if missing: raise RuntimeError("Missing paths: " + repr(missing))
    out = ROOT / NAME
    with zipfile.ZipFile(out, "w") as archive:
        for name in sorted(content):
            if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                raise RuntimeError("Unsafe ZIP path")
            info = zipfile.ZipInfo(name, date_time=(2026,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = ((0o100755 if name.endswith(".command") else 0o100644) << 16)
            archive.writestr(info, content[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=7)
    with zipfile.ZipFile(out) as archive:
        if archive.testzip() or not REQUIRED.issubset(archive.namelist()):
            raise RuntimeError("ZIP invalid")
        for line in archive.read("SHA256SUMS.txt").decode().splitlines():
            digest, name = line.split("  ", 1)
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise RuntimeError("Checksum mismatch: " + name)
        if sha.encode() not in archive.read("BUILD_INFO.txt"):
            raise RuntimeError("Wrong SHA")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    (ROOT / (NAME + ".sha256")).write_text(digest + "  " + NAME + "\n")
    print(f"macOS ZIP: {NAME}; files={len(content)}; commit={sha}; sha256={digest}")

if __name__ == "__main__":
    build()
