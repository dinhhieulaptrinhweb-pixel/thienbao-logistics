@echo off
setlocal
cd /d "%~dp0"
title Thien Bao Website

if not exist ".venv\Scripts\python.exe" (
    echo Website is not installed yet.
    echo Please run SETUP_AND_RUN.bat first.
    pause
    exit /b 1
)

if not exist ".env" copy /Y ".env.example" ".env" >nul

echo Website: http://127.0.0.1:5000
echo Admin:   http://127.0.0.1:5000/admin/login
echo Press CTRL+C to stop.
echo.

start "" "http://127.0.0.1:5000"
".venv\Scripts\python.exe" app.py
pause
