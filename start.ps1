# ============================================================================
# DevOps Agent Platform - Local Startup Script (Windows PowerShell)
# ============================================================================
# This script starts all services for local deployment
# Usage: powershell -File start.ps1

param(
    [switch]$WithKubernetes = $false,
    [switch]$Quick = $false
)

$ErrorActionPreference = "Continue"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Starting DevOps Agent Platform - Local Deployment" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "[1/7] Checking Docker..." -ForegroundColor Yellow
$dockerRunning = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker is running" -ForegroundColor Green
Write-Host ""

# Check .env file exists
Write-Host "[2/7] Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "✗ .env file not found!" -ForegroundColor Red
    Write-Host "  Creating .env from example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✓ Created .env file - Please edit it to add your API keys" -ForegroundColor Yellow
        Write-Host "  Required: OPENAI_API_KEY or ANTHROPIC_API_KEY" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Press Enter after updating .env file..."
        Read-Host
    } else {
        Write-Host "✗ .env.example not found!" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✓ .env file found" -ForegroundColor Green
Write-Host ""

# Start infrastructure services first
Write-Host "[3/7] Starting infrastructure services..." -ForegroundColor Yellow
Write-Host "  - PostgreSQL (Database)" -ForegroundColor Gray
Write-Host "  - RabbitMQ (Message Broker)" -ForegroundColor Gray
Write-Host "  - Redis (Cache)" -ForegroundColor Gray
Write-Host "  - Qdrant (Vector Database)" -ForegroundColor Gray
Write-Host "  - Prometheus (Metrics)" -ForegroundColor Gray
Write-Host "  - Grafana (Visualization)" -ForegroundColor Gray
Write-Host ""

docker-compose up -d postgres rabbitmq redis qdrant prometheus grafana

if (-not $Quick) {
    Write-Host "  Waiting 30 seconds for databases to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 30
    Write-Host "✓ Infrastructure services started" -ForegroundColor Green
} else {
    Start-Sleep -Seconds 5
    Write-Host "✓ Infrastructure services started (quick mode)" -ForegroundColor Green
}
Write-Host ""

# Start agent services
Write-Host "[4/7] Starting AI agents..." -ForegroundColor Yellow
Write-Host "  - LLM Service (OpenAI/Anthropic)" -ForegroundColor Gray
Write-Host "  - Monitoring Agent" -ForegroundColor Gray
Write-Host "  - Analyzer Agent" -ForegroundColor Gray
Write-Host "  - Auto-Response Agent" -ForegroundColor Gray
Write-Host "  - Notifier Agent" -ForegroundColor Gray
Write-Host "  - Worker Service" -ForegroundColor Gray
Write-Host ""

docker-compose up -d llm-service monitoring-agent analyzer-agent auto-response-agent notifier-agent worker

if (-not $Quick) {
    Write-Host "  Waiting 15 seconds for agents to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 15
    Write-Host "✓ AI agents started" -ForegroundColor Green
} else {
    Start-Sleep -Seconds 3
    Write-Host "✓ AI agents started (quick mode)" -ForegroundColor Green
}
Write-Host ""

# Start dashboard services
Write-Host "[5/7] Starting dashboards..." -ForegroundColor Yellow
Write-Host "  - Approval Dashboard (Backend + Frontend)" -ForegroundColor Gray
Write-Host "  - Ops Dashboard (Backend + Frontend)" -ForegroundColor Gray
Write-Host "  - Test Application" -ForegroundColor Gray
Write-Host ""

docker-compose up -d approval-backend approval-frontend ops-dashboard-backend ops-dashboard-frontend test-app

if (-not $Quick) {
    Write-Host "  Waiting 10 seconds for dashboards to build..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
    Write-Host "✓ Dashboards started" -ForegroundColor Green
} else {
    Start-Sleep -Seconds 3
    Write-Host "✓ Dashboards started (quick mode)" -ForegroundColor Green
}
Write-Host ""

# Optional: Start Kubernetes
if ($WithKubernetes) {
    Write-Host "[6/7] Starting Kubernetes cluster..." -ForegroundColor Yellow

    # Check if Kind is available
    $kindPath = ".\infrastructure\kind\..\..\bin\kind.exe"
    if (Test-Path $kindPath) {
        $existingCluster = & $kindPath get clusters 2>&1 | Select-String "devops-agent"
        if ($existingCluster) {
            Write-Host "✓ Kubernetes cluster already exists" -ForegroundColor Green
        } else {
            Write-Host "  Creating Kind cluster (this may take 2-3 minutes)..." -ForegroundColor Gray
            Push-Location "infrastructure\kind"
            & ..\..\bin\kind.exe create cluster --config kind-config-custom.yaml
            Pop-Location
            Write-Host "✓ Kubernetes cluster created" -ForegroundColor Green
        }

        # Deploy to Kubernetes
        Write-Host "  Deploying services to Kubernetes..." -ForegroundColor Gray
        kubectl apply -f infrastructure\kubernetes\base\namespace.yaml
        kubectl apply -f infrastructure\kubernetes\base\rbac.yaml
        kubectl apply -f infrastructure\kubernetes\base\
        kubectl apply -f infrastructure\monitoring\
        Write-Host "✓ Kubernetes deployment complete" -ForegroundColor Green
    } else {
        Write-Host "⊘ Kind not found, skipping Kubernetes setup" -ForegroundColor Yellow
        Write-Host "  Install Kind from: https://kind.sigs.k8s.io/docs/user/quick-start/" -ForegroundColor Gray
    }
    Write-Host ""
} else {
    Write-Host "[6/7] Kubernetes deployment skipped (use -WithKubernetes to enable)" -ForegroundColor Gray
    Write-Host ""
}

# Verify services
Write-Host "[7/7] Verifying services..." -ForegroundColor Yellow
Write-Host ""

$services = docker-compose ps --format json | ConvertFrom-Json
$healthy = 0
$total = 0

foreach ($service in $services) {
    $total++
    $status = $service.Status
    if ($status -match "Up" -or $status -match "healthy") {
        $healthy++
    }
}

Write-Host "  Services running: $healthy / $total" -ForegroundColor Cyan
Write-Host ""

# Show status
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 Access Your Dashboards:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  🎯 Approval Dashboard:  http://localhost:3001" -ForegroundColor White
Write-Host "     Review and approve remediation actions" -ForegroundColor Gray
Write-Host ""
Write-Host "  📈 Ops Dashboard:       http://localhost:3003" -ForegroundColor White
Write-Host "     Real-time incident monitoring" -ForegroundColor Gray
Write-Host ""
Write-Host "  📊 Grafana:             http://localhost:3002" -ForegroundColor White
Write-Host "     Metrics visualization (admin/admin)" -ForegroundColor Gray
Write-Host ""
Write-Host "  🔥 Prometheus:          http://localhost:9090" -ForegroundColor White
Write-Host "     Metrics database & queries" -ForegroundColor Gray
Write-Host ""
Write-Host "  🐰 RabbitMQ:            http://localhost:15672" -ForegroundColor White
Write-Host "     Message queue (devops/devops123)" -ForegroundColor Gray
Write-Host ""

Write-Host "🧪 Test the System:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  # Trigger a CPU spike incident" -ForegroundColor White
Write-Host "  curl -X POST http://localhost:8080/spike/cpu" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Watch agent logs" -ForegroundColor White
Write-Host "  docker-compose logs -f analyzer-agent" -ForegroundColor Gray
Write-Host ""

Write-Host "📝 Useful Commands:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  # View all logs" -ForegroundColor White
Write-Host "  docker-compose logs -f" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Check service status" -ForegroundColor White
Write-Host "  docker-compose ps" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Stop all services" -ForegroundColor White
Write-Host "  powershell -File stop.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Run tests" -ForegroundColor White
Write-Host "  powershell -File run_tests.ps1" -ForegroundColor Gray
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Happy DevOps! 🚀" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
