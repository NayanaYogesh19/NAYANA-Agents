@echo off
echo ====================================
echo FAQ Optimizer Agent - Startup
echo ====================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Check if .env exists
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and fill in your API keys.
    echo.
    pause
    exit /b 1
)

echo.
echo Starting FAQ Optimizer Agent...
echo Server will be available at: http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python backend/main.py

pause
