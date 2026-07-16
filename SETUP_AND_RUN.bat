@echo off
setlocal
cd /d "%~dp0"
title Thien Bao Website Setup

echo ==========================================
echo THIEN BAO WEBSITE - SETUP AND RUN
echo ==========================================
echo.

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
echo Please install Python 3.10 or newer from python.org.
echo IMPORTANT: Check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:python_found
echo Python command found: %PY%
%PY% --version
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 goto failed
)

echo Installing required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed

if not exist ".env" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env configuration file.
)

echo.
echo Setup completed successfully.
echo Website: http://127.0.0.1:5000
echo Admin:   http://127.0.0.1:5000/admin/login
echo.
echo Keep this window open while using the website.
echo Press CTRL+C to stop the website.
echo.

start "" "http://127.0.0.1:5000"
".venv\Scripts\python.exe" app.py
goto end

:failed
echo.
echo ERROR: Setup failed.
echo Please take a screenshot of this window and send it for support.
pause
exit /b 1

:end
pause
