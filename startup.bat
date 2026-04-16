@REM AI Code Maniac - Multi-Agent Code Analysis Platform
@REM Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
@REM
@REM This program is free software: you can redistribute it and/or modify
@REM it under the terms of the GNU General Public License as published by
@REM the Free Software Foundation, either version 3 of the License, or
@REM (at your option) any later version.
@REM
@REM This program is distributed in the hope that it will be useful,
@REM but WITHOUT ANY WARRANTY; without even the implied warranty of
@REM MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
@REM GNU General Public License for more details.
@REM
@REM You should have received a copy of the GNU General Public License
@REM along with this program. If not, see <https://www.gnu.org/licenses/>.
@REM
@REM Author: B.Vignesh Kumar aka Bravetux
@REM Email:  ic19939@gmail.com
@REM Developed: 12th April 2026

@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  AI Code Maniac - Startup
echo ============================================================

:: ── 1. Locate Python ────────────────────────────────────────────
set PYTHON=
for %%P in (python python3) do (
    if not defined PYTHON (
        where %%P >nul 2>&1
        if not errorlevel 1 set PYTHON=%%P
    )
)
if not defined PYTHON (
    echo [ERROR] Python not found. Please install Python 3.11+ and add it to PATH.
    pause
    exit /b 1
)

%PYTHON% --version 2>&1 | findstr /r "3\.[0-9][0-9]" >nul
if errorlevel 1 (
    echo [ERROR] Python 3.10+ required. Found:
    %PYTHON% --version
    pause
    exit /b 1
)
echo [OK] Python: & %PYTHON% --version

:: ── 2. Create venv if missing ───────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment...
    %PYTHON% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment found.
)

:: ── 3. Activate venv ────────────────────────────────────────────
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: ── 4. Upgrade pip silently ─────────────────────────────────────
echo [INFO] Checking pip...
python -m pip install --upgrade pip --quiet

:: ── 5. Check each required package ─────────────────────────────
echo [INFO] Checking required packages...
set MISSING=

:: Read each non-comment, non-blank line from requirements.txt
:: and test whether it is importable or detectable
set NEEDS_INSTALL=0
for /f "tokens=*" %%L in ('type requirements.txt ^| findstr /v "^#" ^| findstr /v "^$"') do (
    :: Strip version specifier — keep only the package name
    set PKG_LINE=%%L
    for /f "tokens=1 delims=><=!" %%N in ("%%L") do (
        set PKG_NAME=%%N
        :: Normalise: replace hyphen with underscore for import check
        set PKG_IMPORT=%%N
        set PKG_IMPORT=!PKG_IMPORT:-=_!
    )
    python -c "import importlib.util; import sys; n='!PKG_IMPORT!'.lower(); found=importlib.util.find_spec(n) is not None or any(n in d.lower() for d in sys.path); exit(0 if found else 1)" >nul 2>&1
    if errorlevel 1 (
        :: Fallback: use pip show
        pip show !PKG_NAME! >nul 2>&1
        if errorlevel 1 (
            echo   [MISSING] !PKG_NAME!
            set NEEDS_INSTALL=1
        )
    )
)

if !NEEDS_INSTALL! == 1 (
    echo [INFO] Installing missing packages from requirements.txt...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Package installation failed. Check your internet connection.
        pause
        exit /b 1
    )
    echo [OK] All packages installed.
) else (
    echo [OK] All required packages are already installed.
)

:: ── 6. Create .env if missing ───────────────────────────────────
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [INFO] Created .env from .env.example — please fill in your credentials.
    )
)

:: ── 7. Create data directory if missing ─────────────────────────
if not exist "data" mkdir data

:: ── 7b. Free port 8501 and kill stale Streamlit processes ────────
echo [INFO] Checking for processes on port 8501...
set PORT_FREE=1
for /f "tokens=5" %%P in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8501 "') do (
    if not "%%P"=="0" (
        echo   [KILL] Port 8501 held by PID %%P — terminating.
        taskkill /PID %%P /F >nul 2>&1
        set PORT_FREE=0
    )
)
if !PORT_FREE! == 0 (
    :: Wait briefly for the port to release
    timeout /t 2 /nobreak >nul
    :: Verify port is now free
    netstat -ano | findstr "LISTENING" | findstr ":8501 " >nul 2>&1
    if not errorlevel 1 (
        echo [WARN] Port 8501 still occupied — retrying with force...
        for /f "tokens=5" %%P in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8501 "') do (
            taskkill /PID %%P /F >nul 2>&1
        )
        timeout /t 2 /nobreak >nul
    )
)
echo [OK] Port 8501 is free.

:: ── 7c. Clear stale database locks ─────────────────────────────────
echo [INFO] Checking for stale processes holding the database...
set DB_FILE=%~dp0data\arena.db

:: Kill any remaining Streamlit python processes (belt-and-suspenders)
for /f "tokens=2" %%P in ('wmic process where "name='python.exe'" get processid^,commandline /value 2^>nul ^| findstr /i "streamlit" ^| findstr /r "ProcessId=[0-9]"') do (
    echo   [KILL] Streamlit process PID %%P — terminating.
    taskkill /PID %%P /F >nul 2>&1
)

:: Verify the DB lock is now free; if not, fall back to killing all python.exe
if exist "%DB_FILE%" (
    python -c "import duckdb; c=duckdb.connect(r'%DB_FILE%'); c.close()" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] DB still locked — killing all python.exe processes...
        taskkill /IM python.exe /F >nul 2>&1
        taskkill /IM python3.exe /F >nul 2>&1
        timeout /t 2 /nobreak >nul
    )
)
echo [OK] Database lock clear.

:: ── 8. Set PYTHONPATH so all app pages can import project modules ─
:: Streamlit adds app/ to sys.path by default; we also need the project root.
set PYTHONPATH=%~dp0

:: ── 9. Launch the app ───────────────────────────────────────────
:: To expose on the network (LAN access), uncomment the next line
:: and comment out the localhost-only line below it:
::   set NETWORK_MODE=1
set NETWORK_MODE=0

echo.
echo ============================================================
echo  Starting AI Code Maniac...
if !NETWORK_MODE! == 1 (
    echo  Local:   http://localhost:8501
    echo  Network: http://0.0.0.0:8501
) else (
    echo  Open http://localhost:8501 in your browser
)
echo  Press Ctrl+C to stop
echo ============================================================
echo.

if !NETWORK_MODE! == 1 (
    streamlit run app/Home.py --server.address 0.0.0.0
) else (
    streamlit run app/Home.py --server.address localhost
)

endlocal
