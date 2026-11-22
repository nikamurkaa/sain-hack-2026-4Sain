"""Deterministic portable Windows candidate built from exactly the checkout SHA.

Offline packaging only: never calls the organizer's APIs, models, or simulator.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "SAIN-Smart-Room-Portfolio-Windows.zip"
IGNORED_PARTS = {".git", ".github", ".venv", ".runtime", "node_modules", "__pycache__", "test-results", ".pytest_cache"}
FORBIDDEN_ENDINGS = (".pem", ".p12", ".pfx", ".key", ".ppk")
ROOT_ALIASES = {
    "docs/WINDOWS_ACCEPTANCE_GUIDE_RU.md": "WINDOWS_ACCEPTANCE_GUIDE_RU.md",
}
REQUIRED = {
    "BUILD_INFO.txt", "README_WINDOWS.md", "CHECK_ENV.cmd", "START.cmd", "STOP.cmd",
    "RESET_TEST_STATE.cmd", "launcher.ps1", "stop.ps1", "check_env.ps1",
    "main.py", "requirements-dev.txt", "frontend/serve.py", "frontend/dist/index.html",
    "WINDOWS_ACCEPTANCE_GUIDE_RU.md",
}


def tracked():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    for raw in result.split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw))
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if relative.name.startswith(".env") or relative.name.lower().endswith(FORBIDDEN_ENDINGS):
            continue
        if relative.suffix.lower() in {".zip", ".tar", ".gz"}:
            continue
        full = ROOT / relative
        if full.is_symlink() or not full.is_file():
            continue
        yield relative


def package():
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    ci_sha = os.getenv("GITHUB_SHA")
    if ci_sha and ci_sha != sha:
        raise RuntimeError("GitHub run SHA does not match checked-out source")
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError("Frontend build missing: run npm ci and npm run build")
    out = ROOT / NAME
    content = {}
    for relative in tracked():
        src = ROOT / relative
        if relative.parts[0] == "windows":
            target = Path(*relative.parts[1:]).as_posix()
        else:
            target = relative.as_posix()
        content[target] = src.read_bytes()
        if relative.as_posix() in ROOT_ALIASES:
            content[ROOT_ALIASES[relative.as_posix()]] = content[target]
    for src in sorted((ROOT / "frontend/dist").rglob("*")):
        if src.is_file() and not src.is_symlink():
            relative = src.relative_to(ROOT).as_posix()
            content[relative] = src.read_bytes()
    content["README_WINDOWS.md"] = (
        "# SAIN Smart Room — проверка на Windows\n\n"
        "Это портфолио-прототип. Нативный Windows запуск проверяется отдельно. "
        "Откройте CHECK_ENV.cmd, затем START.cmd. Режим 1 — локальная репетиция "
        "с FakeLLM/MockSimulator, режим 2 — официальный стенд с временным ГОСТЕВЫМ токеном. "
        "Командный ключ никогда не вводить в браузер.\n\n"
        "Для локального токена в CMD из корня архива выполните "
        r".venv\Scripts\python.exe -m scripts.client_access dev --stay stay_test"
        "\n\nПолная пошаговая инструкция: WINDOWS_ACCEPTANCE_GUIDE_RU.md. "
        "Остановка: STOP.cmd; сброс репетиции: RESET_TEST_STATE.cmd.\n"
    ).encode("utf-8")
    content["BUILD_INFO.txt"] = (
        "SAIN Smart Room / 4Sain / Windows Portfolio Demo\n"
        f"GitHub source SHA: {sha}\n"
        "Built from GitHub Actions checkout with npm ci + npm test + npm run build.\n"
        "CI workflow: windows-package.yml; browser E2E separately checked by frontend.yml.\n"
        "Windows native launch: NOT YET VERIFIED. Final guest: READ ONLY.\n"
        "REHEARSAL: FakeLLM + MockSimulator. STAND: official temporary GUEST token only.\n"
        "No official /run, production deploy, or organizer quota used in packaging.\n"
    ).encode("utf-8")
    missing = REQUIRED - content.keys()
    if missing:
        raise RuntimeError(f"Windows package missing required paths: {sorted(missing)}")
    checksums = {
        name: hashlib.sha256(blob).hexdigest() for name, blob in sorted(content.items())
    }
    content["SHA256SUMS.txt"] = (
        "\n".join(f"{digest}  {name}" for name, digest in checksums.items()) + "\n"
    ).encode()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7, strict_timestamps=False) as archive:
        for name in sorted(content):
            if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                raise RuntimeError("Unsafe ZIP path: " + name)
            archive.writestr(name, content[name])
    with zipfile.ZipFile(out) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC verification failed")
        if not REQUIRED.issubset(archive.namelist()):
            raise RuntimeError("Required entries absent from ZIP")
        stored = archive.read("SHA256SUMS.txt").decode()
        for line in stored.splitlines():
            digest, name = line.split("  ", 1)
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise RuntimeError("SHA256 mismatch: " + name)
        if sha.encode() not in archive.read("BUILD_INFO.txt"):
            raise RuntimeError("Incorrect SHA in BUILD_INFO")
    archive_digest = hashlib.sha256(out.read_bytes()).hexdigest()
    (ROOT / (NAME + ".sha256")).write_text(archive_digest + "  " + NAME + "\n")
    print(f"Windows ZIP: {out}; files={len(content)}; SHA={sha}; sha256={archive_digest}")


if __name__ == "__main__":
    package()
