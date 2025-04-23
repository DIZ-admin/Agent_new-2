@echo off
REM Setup script for local development environment on Windows

echo Setting up local development environment for Photo Agent...

REM Create necessary directories if they don't exist
mkdir data\downloads data\metadata data\analysis data\upload\metadata data\uploaded data\reports data\registry data\processed logs 2>nul

REM Check if Docker is installed
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Docker is not installed. Please install Docker and Docker Compose first.
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Docker Compose is not installed. Please install Docker Compose first.
    exit /b 1
)

REM Build the Docker image
echo Building Docker image for local development...
docker-compose -f docker-compose.local.yml build

echo.
echo Local development environment setup complete!
echo.
echo To start the application in local mode, run:
echo   docker-compose -f docker-compose.local.yml up
echo.
echo The web interface will be available at: http://localhost:8080
echo.
echo Note: In local mode, SharePoint and OpenAI services are mocked.
echo To use real services, edit config/config.local.env and set:
echo   MOCK_SHAREPOINT=false
echo   MOCK_OPENAI=false
echo And provide valid credentials/API keys.
