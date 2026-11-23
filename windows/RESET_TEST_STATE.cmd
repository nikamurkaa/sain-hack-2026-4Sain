@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
if errorlevel 1 exit /b 1
echo [SAIN] RESET will permanently delete ONLY local synthetic demo sessions and history.
echo [SAIN] Normal STOP/START preserves valid sessions; do not reset before a demo.
choice /C YN /N /M "Delete .sain-state database now? [Y/N] "
if errorlevel 2 (
  echo [SAIN] Reset cancelled. Data preserved.
  exit /b 0
)
if exist "%~dp0.sain-state" (
  powershell.exe -NoProfile -Command "Remove-Item -LiteralPath '%~dp0.sain-state' -Recurse -Force -ErrorAction Stop"
  if errorlevel 1 (
    echo [SAIN] Failed to delete state. Ensure all backends have stopped.
    exit /b 1
  )
)
echo [SAIN] Local synthetic demo database removed. START.cmd creates a new one.
exit /b 0
