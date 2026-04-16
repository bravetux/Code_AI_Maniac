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
setlocal

echo ============================================================
echo  Markdown to HTML Converter
echo ============================================================

:: ── Validate input ──────────────────────────────────────────────
if "%~1"=="" (
    echo.
    echo Usage: md2html.bat ^<input.md^> [output.html]
    echo.
    echo   input.md    - Path to the Markdown file to convert
    echo   output.html - Optional output path ^(default: same name with .html^)
    echo.
    echo Examples:
    echo   md2html.bat README.md
    echo   md2html.bat docs\effort.md docs\effort.html
    exit /b 1
)

if not exist "%~1" (
    echo [ERROR] File not found: %~1
    exit /b 1
)

:: ── Locate Python ───────────────────────────────────────────────
set PYTHON=
for %%P in (python python3) do (
    if not defined PYTHON (
        where %%P >nul 2>&1
        if not errorlevel 1 set PYTHON=%%P
    )
)
if not defined PYTHON (
    echo [ERROR] Python not found. Please install Python 3 and add it to PATH.
    exit /b 1
)

:: ── Run converter ───────────────────────────────────────────────
set SCRIPT=%~dp0tools\md_to_html.py
if not exist "%SCRIPT%" (
    echo [ERROR] Converter script not found: %SCRIPT%
    exit /b 1
)

if "%~2"=="" (
    %PYTHON% "%SCRIPT%" "%~1"
) else (
    %PYTHON% "%SCRIPT%" "%~1" "%~2"
)

endlocal
