@echo off
title CRS setup
cd /d "%~dp0"

python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)" 2>nul
if errorlevel 1 (
  echo Python 3.11 or newer is required. Install it from python.org, tick "Add python.exe to PATH", then run this again.
  pause
  exit /b 1
)

echo Setting up CRS. This installs its packages and downloads about 4 GB of models, one time only.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup_env.ps1 %*
if errorlevel 1 goto failed
.venv\Scripts\python.exe scripts\fetch_resources.py --app-only
if errorlevel 1 goto failed
.venv\Scripts\python.exe scripts\fetch_adapters.py
if errorlevel 1 goto failed

echo.
echo Setup finished. Double-click start_app.bat to open CRS.
pause
exit /b 0

:failed
echo.
echo Setup did not finish. Check your internet connection, then run this again. Finished downloads are kept.
pause
exit /b 1
