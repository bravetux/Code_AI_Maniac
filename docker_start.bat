@REM AI Code Maniac - Docker Startup
@REM Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
@REM
@REM This program is free software: you can redistribute it and/or modify
@REM it under the terms of the GNU General Public License as published by
@REM the Free Software Foundation, either version 3 of the License, or
@REM (at your option) any later version.

@echo off
setlocal EnableDelayedExpansion

set IMAGE_NAME=ai-code-maniac
set CONTAINER_NAME=aicm
set HOST_PORT=8501
set CONTAINER_PORT=8501

echo ============================================================
echo  AI Code Maniac - Docker Startup
echo ============================================================

:: -- 1. Verify Docker is installed and running -----------------
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found. Install Docker Desktop and ensure it is on PATH.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running. Start Docker Desktop and retry.
    pause
    exit /b 1
)
echo [OK] Docker is available.

:: -- 2. Ensure .env exists -------------------------------------
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [INFO] Created .env from .env.example - fill in AWS credentials before re-running.
        pause
        exit /b 1
    ) else (
        echo [ERROR] No .env file found and no .env.example to copy from.
        pause
        exit /b 1
    )
)
echo [OK] .env present.

:: -- 3. Ensure host directories exist for volume mounts --------
if not exist "data" mkdir data
if not exist "Reports" mkdir Reports
echo [OK] Host data\ and Reports\ directories ready.

:: -- 4. Stop and remove any existing container -----------------
docker ps -a --format "{{.Names}}" | findstr /b /e "%CONTAINER_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Removing existing container %CONTAINER_NAME%...
    docker rm -f %CONTAINER_NAME% >nul 2>&1
    echo [OK] Old container removed.
)

:: -- 5. Build the image ----------------------------------------
echo [INFO] Building image %IMAGE_NAME% (this may take several minutes the first time)...
docker build -t %IMAGE_NAME% .
if errorlevel 1 (
    echo [ERROR] Docker build failed.
    pause
    exit /b 1
)
echo [OK] Image built.

:: -- 6. Free the host port if held by something else -----------
for /f "tokens=5" %%P in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%HOST_PORT% "') do (
    if not "%%P"=="0" (
        echo [WARN] Port %HOST_PORT% held by PID %%P - terminating.
        taskkill /PID %%P /F >nul 2>&1
    )
)

:: -- 7. Run the container --------------------------------------
echo.
echo ============================================================
echo  Starting container %CONTAINER_NAME% on port %HOST_PORT%
echo  Open http://localhost:%HOST_PORT% in your browser
echo  View logs: docker logs -f %CONTAINER_NAME%
echo  Stop:      docker stop %CONTAINER_NAME%
echo ============================================================
echo.

docker run -d ^
    --name %CONTAINER_NAME% ^
    -p %HOST_PORT%:%CONTAINER_PORT% ^
    --env-file .env ^
    -v "%cd%\data:/app/data" ^
    -v "%cd%\Reports:/app/Reports" ^
    --restart unless-stopped ^
    %IMAGE_NAME%

if errorlevel 1 (
    echo [ERROR] Failed to start container.
    pause
    exit /b 1
)

echo [OK] Container started.
echo.
echo Tailing logs (Ctrl+C to detach - container keeps running)...
echo.
docker logs -f %CONTAINER_NAME%

endlocal
