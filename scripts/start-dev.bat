@echo off
echo ====================================
echo Starting DevLeague Hackathon Stack
echo ====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Node is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/3] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some Python dependencies may have failed to install
)

echo.
echo [2/3] Installing Frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo [3/3] Starting servers...
echo.
echo Backend will run on: http://localhost:8000
echo Frontend will run on: http://localhost:8443
echo.
echo Press Ctrl+C in either window to stop the servers
echo.

REM Start backend in a new window
start "Backend Server (Port 8000)" cmd /k "cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
start "Frontend Server (Port 8443)" cmd /k "cd frontend && npm run dev"

echo.
echo ====================================
echo Servers are starting!
echo ====================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:8443
echo API Docs: http://localhost:8000/docs
echo.
echo Check the new terminal windows for server logs
echo.
pause
