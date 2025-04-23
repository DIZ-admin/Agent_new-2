@echo off
REM Script for running the local Photo Agent container

REM Function to display help
:show_help
    echo Usage: run-local.bat [COMMAND]
    echo.
    echo Commands:
    echo   start       Start the container in detached mode
    echo   stop        Stop the container
    echo   restart     Restart the container
    echo   logs        Show container logs
    echo   shell       Open a shell in the container
    echo   web         Start the web interface (default)
    echo   process     Run the full processing pipeline
    echo   schema      Get metadata schema
    echo   photos      Process photos
    echo   analyze     Analyze photos with OpenAI
    echo   metadata    Generate metadata
    echo   upload      Upload to SharePoint
    echo   build       Rebuild the Docker image
    echo   help        Show this help message
    echo.
    exit /b 0

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Process command
if "%1"=="" goto :show_help

if "%1"=="start" (
    echo Starting Photo Agent container in detached mode...
    docker-compose -f docker-compose.local.yml up -d
    echo Container started. Web interface available at http://localhost:8080
    exit /b 0
)

if "%1"=="stop" (
    echo Stopping Photo Agent container...
    docker-compose -f docker-compose.local.yml down
    exit /b 0
)

if "%1"=="restart" (
    echo Restarting Photo Agent container...
    docker-compose -f docker-compose.local.yml down
    docker-compose -f docker-compose.local.yml up -d
    echo Container restarted. Web interface available at http://localhost:8080
    exit /b 0
)

if "%1"=="logs" (
    echo Showing container logs (press Ctrl+C to exit)...
    docker-compose -f docker-compose.local.yml logs -f
    exit /b 0
)

if "%1"=="shell" (
    echo Opening shell in the container...
    docker-compose -f docker-compose.local.yml exec agent bash
    exit /b 0
)

if "%1"=="web" (
    echo Starting web interface...
    docker-compose -f docker-compose.local.yml down
    docker-compose -f docker-compose.local.yml up
    exit /b 0
)

if "%1"=="process" (
    echo Running full processing pipeline...
    docker-compose -f docker-compose.local.yml run --rm agent python -m src.auto_process
    exit /b 0
)

if "%1"=="schema" (
    echo Getting metadata schema...
    docker-compose -f docker-compose.local.yml run --rm agent python -m src.metadata_schema
    exit /b 0
)

if "%1"=="photos" (
    echo Processing photos...
    docker-compose -f docker-compose.local.yml run --rm agent python -m src.photo_metadata
    exit /b 0
)

if "%1"=="analyze" (
    echo Analyzing photos with OpenAI...
    docker-compose -f docker-compose.local.yml run --rm agent python -m src.openai_analyzer
    exit /b 0
)

if "%1"=="metadata" (
    echo Generating metadata...
    docker-compose -f docker-compose.local.yml run --rm agent python -m src.metadata_generator
    exit /b 0
)

if "%1"=="upload" (
    echo Uploading to SharePoint...
    docker-compose -f docker-compose.local.yml run --rm agent python -m src.sharepoint_uploader
    exit /b 0
)

if "%1"=="build" (
    echo Rebuilding Docker image...
    docker-compose -f docker-compose.local.yml build
    exit /b 0
)

if "%1"=="help" (
    goto :show_help
) else (
    goto :show_help
)
