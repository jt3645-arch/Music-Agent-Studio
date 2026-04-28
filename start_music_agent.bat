@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "PYTHON_EXE=%BACKEND%\.venv\Scripts\python.exe"

echo =====================================
echo AI Music Agent Studio - One Click Run
echo =====================================
echo.

if not exist "%PYTHON_EXE%" (
  echo Backend virtual environment was not found.
  echo Please run setup_music_agent.bat first.
  pause
  exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
  echo Frontend dependencies were not found.
  echo Please run setup_music_agent.bat first.
  pause
  exit /b 1
)

echo Starting backend...
start "Music Agent Backend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%BACKEND%'; & '%PYTHON_EXE%' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Starting frontend...
start "Music Agent Frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%FRONTEND%'; npm.cmd run dev -- --hostname 127.0.0.1 --port 3000"

echo.
echo Waiting a few seconds before opening the app...
timeout /t 6 /nobreak >nul
start "" "http://127.0.0.1:3000"

echo.
echo App should be opening in your browser.
echo Keep both terminal windows open while using the app.
pause
