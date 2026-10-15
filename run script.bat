@echo off
cd /d "%~dp0"
title Shuffle Master - Terminal Interface

echo =======================================================================
echo                 S H U F F L E // M A S T E R
echo                     Terminal Audio Shuffler
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

python -c "import rich, mutagen" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo [INFO] Starting terminal interface...
echo.
python -m terminal.main

if errorlevel 1 (
    echo.
    echo [NOTE] Application exited with error code %errorlevel%.
    pause
    exit /b 1
)

echo.
echo Application closed.
pause
exit /b 0
