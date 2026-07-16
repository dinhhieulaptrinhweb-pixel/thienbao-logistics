@echo off
setlocal
cd /d "%~dp0"
title Thien Bao Website Setup

where py >nul 2>&1
if not errorlevel 1 (
    set "PY=py"
    goto python_found
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
    goto python_found
)

echo ERROR: Python was not found.
echo Install Python 3.10 or newer and enable Add Python to PATH.
pause
exit /b 1

:python_found
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if errorlevel 1 goto failed

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed

if not exist ".env" copy /Y ".env.example" ".env" >nul

echo.
echo SETUP COMPLETED.
echo Run START_WEBSITE.bat to open the website.
pause
exit /b 0

:failed
echo SETUP FAILED.
pause
exit /b 1
