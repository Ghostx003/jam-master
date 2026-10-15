@echo off
cd /d "%~dp0"
title Shuffle Master - Web Application Backend

echo =======================================================================
echo                 S H U F F L E // M A S T E R
echo                    Modern Web Application
echo =======================================================================
echo.

if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
) else if exist "%~dp0venv\Scripts\activate.bat" (
    call "%~dp0venv\Scripts\activate.bat"
)

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH or virtual environment!
    echo Please install Python 3.10+ from python.org and add it to your PATH.
    echo.
    pause
    exit /b 1
)

python -c "import fastapi, uvicorn, mutagen, rich" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required backend dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
)

echo [INFO] Checking port 127.0.0.1:8765 and restarting server...
python -c "import subprocess, re; [subprocess.run(['taskkill', '/f', '/pid', m.group(1)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for line in subprocess.getoutput('netstat -ano').splitlines() if ':8765' in line and 'LISTENING' in line and (m := re.search(r'\s+(\d+)$', line.strip()))]" >nul 2>&1



echo [INFO] Starting Shuffle Master server on http://127.0.0.1:8765 ...
echo [INFO] Opening web application in default browser...
echo [NOTE] Keep this window open while using Shuffle Master. Close it to stop the server.
echo.
python -m backend.server --open-browser

if errorlevel 1 (
    echo.
    echo [NOTE] Server exited with error code %errorlevel%.
    pause
    exit /b 1
)

echo.
echo [NOTE] Server has stopped.
pause
exit /b 0
