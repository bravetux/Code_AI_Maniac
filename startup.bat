@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  AI Arena - Startup
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

:: ── 8. Launch the app ───────────────────────────────────────────
echo.
echo ============================================================
echo  Starting AI Arena...
echo  Open http://localhost:8501 in your browser
echo  Press Ctrl+C to stop
echo ============================================================
echo.
streamlit run app/Home.py

endlocal
