@echo off
setlocal EnableExtensions
title SwissTech Stock Tracker

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
set "COMPOSE_FILE=%REPO_ROOT%\deployment\docker-compose.prod.yml"
set "ENV_FILE=%REPO_ROOT%\deployment\.env.prod"

if not exist "%ENV_FILE%" goto missing_config

where docker >nul 2>&1
if errorlevel 1 goto missing_docker

docker info >nul 2>&1
if errorlevel 1 (
  echo Starting Docker Desktop. This can take up to two minutes...
  if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
  ) else (
    goto missing_docker
  )

  for /L %%I in (1,1,60) do (
    docker info >nul 2>&1
    if not errorlevel 1 goto docker_ready
    timeout /t 2 /nobreak >nul
  )
  goto docker_failed
)

:docker_ready
echo Starting SwissTech Stock Tracker...
docker compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" up -d
if errorlevel 1 goto app_failed

set "HTTP_PORT=8080"
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /c:"HTTP_PORT=" "%ENV_FILE%"`) do set "HTTP_PORT=%%B"
set "APP_URL=http://localhost:%HTTP_PORT%"

echo Waiting for the application...
for /L %%I in (1,1,60) do (
  powershell.exe -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%APP_URL%/api/v1/health/' -TimeoutSec 3; if ($r.StatusCode -eq 200) { exit 0 } }; exit 1" >nul 2>&1
  if not errorlevel 1 goto app_ready
  timeout /t 2 /nobreak >nul
)
goto app_timeout

:app_ready
echo Opening %APP_URL%
start "" "%APP_URL%"
exit /b 0

:missing_config
echo.
echo SETUP INCOMPLETE: deployment\.env.prod is missing.
echo Ask the technician to complete LOCAL_SETUP_GUIDE.md.
goto pause_error

:missing_docker
echo.
echo Docker Desktop is not installed or Docker is not available in PATH.
echo Ask the technician to install Docker Desktop for Windows.
goto pause_error

:docker_failed
echo.
echo Docker Desktop did not start. Open it manually, wait until it is ready,
echo then double-click the Stock Tracker icon again.
goto pause_error

:app_failed
echo.
echo Stock Tracker could not start. Ask the technician to check Docker logs.
goto pause_error

:app_timeout
echo.
echo Stock Tracker started but did not become ready within two minutes.
echo Ask the technician to check Docker logs.

:pause_error
echo.
pause
exit /b 1
