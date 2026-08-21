@echo off
setlocal

REM Always resolve paths from the repository root, even when this file is
REM launched from Explorer or from a different working directory.
for %%I in ("%~dp0..") do set "STAYLONGER_ROOT=%%~fI"
set "STAYLONGER_VENV=%STAYLONGER_ROOT%\.venv"
set "STAYLONGER_PYTHON=%STAYLONGER_VENV%\Scripts\python.exe"

pushd "%STAYLONGER_ROOT%" || exit /b 1

echo ====================================
echo Starting StayLongerAI demo stack
echo ====================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or is not available on PATH.
    popd
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or is not available on PATH.
    popd
    exit /b 1
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm is not installed or is not available on PATH.
    popd
    exit /b 1
)

if not exist "%STAYLONGER_PYTHON%" (
    echo [1/4] Creating isolated Python environment...
    python -m venv "%STAYLONGER_VENV%"
    if errorlevel 1 goto :failure
) else (
    echo [1/4] Using existing Python environment.
)

echo [2/4] Installing backend dependencies...
"%STAYLONGER_PYTHON%" -m pip install -r "%STAYLONGER_ROOT%\requirements.txt"
if errorlevel 1 goto :failure

echo [3/4] Installing frontend dependencies...
pushd "%STAYLONGER_ROOT%\frontend" || goto :failure
call npm.cmd install
if errorlevel 1 (
    popd
    goto :failure
)
popd

if not exist "%STAYLONGER_ROOT%\backend\.env" (
    echo.
    echo NOTE: backend\.env is missing. The app will run in demo mode.
    echo       Copy backend\.env.example to backend\.env to configure Twilio.
)

echo [4/4] Starting backend and frontend...
start "StayLongerAI Backend - 8000" /D "%STAYLONGER_ROOT%\backend" cmd /k ""%STAYLONGER_PYTHON%" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
start "StayLongerAI Frontend - 8443" /D "%STAYLONGER_ROOT%\frontend" cmd /k "npm.cmd run dev"

echo.
echo Backend:  http://localhost:8000
echo API docs: http://localhost:8000/docs
echo Frontend: http://localhost:8443
echo.
echo Each server runs in its own terminal window. Close both windows to stop.
popd
exit /b 0

:failure
echo.
echo ERROR: Setup failed. Review the message above and try again.
popd
exit /b 1
