@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" %*
set "SAIN_EXIT=%ERRORLEVEL%"
if not "%SAIN_EXIT%"=="0" echo [SAIN] Startup failed. Check the error above.
if not "%SAIN_CI%"=="1" pause
exit /b %SAIN_EXIT%
