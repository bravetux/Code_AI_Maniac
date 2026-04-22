@echo off
REM Start the F20 CI/CD webhook receiver.
REM Requires: pip install fastapi uvicorn
cd /d "%~dp0\.."
call venv\Scripts\activate.bat 2>nul
set PYTHONPATH=%CD%
uvicorn tools.webhook_server:app --host 0.0.0.0 --port %WEBHOOK_PORT%
if "%ERRORLEVEL%"=="9009" (
    echo uvicorn not found. Install with: pip install fastapi uvicorn
    pause
)
