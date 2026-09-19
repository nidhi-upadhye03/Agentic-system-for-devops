@echo off
REM Quick Start Script for AI-Driven Kubernetes System - Windows

echo ==========================================
echo AI-Driven Kubernetes System - Quick Start
echo ==========================================
echo.

REM Check if Docker is running
echo Checking Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo.
    echo Please:
    echo 1. Make sure Docker Desktop is installed
    echo 2. Start Docker Desktop
    echo 3. Wait for Docker to fully start (check system tray icon^)
    echo 4. Run this script again
    pause
    exit /b 1
)

echo Docker is running
echo.

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo.
    echo Please:
    echo 1. Copy .env.example to .env
    echo 2. Add your OpenAI or Gemini API key to .env
    echo 3. Run this script again
    pause
    exit /b 1
)

echo .env file found
echo.

REM Check for API keys
findstr /C:"your-openai-key-here" .env >nul && findstr /C:"your-gemini-key-here" .env >nul
if %errorlevel% equ 0 (
    echo WARNING: No API keys configured!
    echo.
    echo The system will start, but LLM features won't work.
    echo Please add your OpenAI or Gemini API key to .env file.
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
)

echo Starting all services...
echo.

REM Start services
docker-compose up -d

echo.
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo ==========================================
echo Services Started!
echo ==========================================
echo.
echo Web Interfaces:
echo    Approval Dashboard:  http://localhost:3001
echo    LLM Service API:     http://localhost:8000/docs
echo    RabbitMQ Management: http://localhost:15672 (guest/guest^)
echo    Grafana Dashboards:  http://localhost:3002 (admin/admin^)
echo    Prometheus:          http://localhost:9090
echo    Qdrant Dashboard:    http://localhost:6333/dashboard
echo.
echo Default Credentials:
echo    Approval Dashboard:  admin@approvaldashboard.com / Admin@123
echo    RabbitMQ:            guest / guest
echo    Grafana:             admin / admin
echo.
echo Check service status:
echo    docker-compose ps
echo.
echo View logs:
echo    docker-compose logs -f [service-name]
echo.
echo Stop all services:
echo    docker-compose down
echo.
echo ==========================================
echo.
pause
