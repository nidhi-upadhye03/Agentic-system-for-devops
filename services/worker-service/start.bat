@echo off
REM Start script for Worker Service (Windows)

echo Starting Worker Service...

REM Check if .env file exists
if not exist .env (
    echo Warning: .env file not found. Copying from .env.example
    copy .env.example .env
    echo Please update .env with your configuration before running in production
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Run the worker
echo Starting worker service...
python -m app.main
