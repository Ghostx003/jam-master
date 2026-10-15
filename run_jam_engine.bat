@echo off
title JAM//ENGINE
chcp 65001 > nul
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your PATH.
    echo Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

python main.py %*

if %errorlevel% neq 0 (
    echo.
    echo [JAM//ENGINE stopped with an unexpected error]
    pause
)
