@echo off
title CRS
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo The Python environment is missing. Follow the setup steps in README.md first.
  pause
  exit /b 1
)
if not exist "models\qwen2.5-1.5b\config.json" (
  echo The model files are missing. Follow the setup steps in README.md first.
  pause
  exit /b 1
)
if not exist "app\web\dist\index.html" (
  echo The built interface is missing from app\web\dist.
  pause
  exit /b 1
)

echo Starting CRS. Your browser will open when the model is ready.
set CRS_OPEN_BROWSER=1
.venv\Scripts\python.exe -m app.server
echo.
echo CRS has stopped.
pause
