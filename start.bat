@echo off
cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is required but not found.
    echo Install it from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

echo.
echo Starting music player server at http://localhost:8080
echo Press Ctrl+C to stop.
echo.
python server.py %*
