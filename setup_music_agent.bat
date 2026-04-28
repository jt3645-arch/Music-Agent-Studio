@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "PYTHON_EXE=%BACKEND%\.venv\Scripts\python.exe"

echo ========================================
echo AI Music Agent Studio - First Time Setup
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python 3.10 or 3.11 first.
  pause
  exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Please install Node.js 18 or newer first.
  pause
  exit /b 1
)

if not exist "%PYTHON_EXE%" (
  echo Creating backend virtual environment...
  python -m venv "%BACKEND%\.venv"
  if errorlevel 1 (
    echo Failed to create the backend virtual environment.
    pause
    exit /b 1
  )
)

echo Installing backend dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r "%BACKEND%\requirements.txt"
if errorlevel 1 (
  echo Failed to install backend dependencies.
  pause
  exit /b 1
)

echo Installing frontend dependencies...
pushd "%FRONTEND%"
npm.cmd install
if errorlevel 1 (
  popd
  echo Failed to install frontend dependencies.
  pause
  exit /b 1
)
popd

echo.
echo Setup complete. You can now run start_music_agent.bat
pause

