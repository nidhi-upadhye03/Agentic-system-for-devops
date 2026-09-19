# ============================================================================
# DevOps Agent Platform - Verification Script (Windows PowerShell)
# ============================================================================
# This script verifies all services are running correctly
# Usage: powershell -File verify.ps1

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  DevOps Agent Platform - Health Check" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

$allHealthy = $true

# Check Docker Compose Services
Write-Host "📦 Docker Compose Services:" -ForegroundColor Yellow
Write-Host ""

$services = @(
    @{Name="postgres"; Port=5432; Health="docker-compose exec postgres pg_isready"},
    @{Name="rabbitmq"; Port=15672; Health="http://localhost:15672/api/health/checks/alarms"},
    @{Name="redis"; Port=6379; Health="docker-compose exec redis redis-cli PING"},
    @{Name="qdrant"; Port=6333; Health="http://localhost:6333"},
    @{Name="prometheus"; Port=9090; Health="http://localhost:9090/-/healthy"},
    @{Name="grafana"; Port=3002; Health="http://localhost:3002/api/health"},
    @{Name="llm-service"; Port=8000; Health="http://localhost:8000/health"},
    @{Name="approval-backend"; Port=3000; Health="http://localhost:3000/api/health"},
    @{Name="approval-frontend"; Port=3001; Health="http://localhost:3001"},
    @{Name="ops-dashboard-backend"; Port=8001; Health="http://localhost:8001/api/health"},
    @{Name="ops-dashboard-frontend"; Port=3003; Health="http://localhost:3003/health"},
    @{Name="test-app"; Port=8080; Health="http://localhost:8080/health"}
)

foreach ($service in $services) {
    $name = $service.Name
    $port = $service.Port
    $healthCheck = $service.Health

    # Check if container is running
    $container = docker ps --filter "name=devops-$name" --format "{{.Status}}"

    if ($container) {
        Write-Host "  ✓ $name" -ForegroundColor Green -NoNewline
        Write-Host " (port $port) - " -ForegroundColor Gray -NoNewline

        # Try health check if it's an HTTP endpoint
        if ($healthCheck -match "^http") {
            try {
                $response = Invoke-WebRequest -Uri $healthCheck -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Host "Healthy" -ForegroundColor Green
                } else {
                    Write-Host "Running (status: $($response.StatusCode))" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "Running (health check failed)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "Running" -ForegroundColor Green
        }
    } else {
        Write-Host "  ✗ $name" -ForegroundColor Red -NoNewline
        Write-Host " - Not running" -ForegroundColor Red
        $allHealthy = $false
    }
}

Write-Host ""

# Check Agents
Write-Host "🤖 AI Agents:" -ForegroundColor Yellow
Write-Host ""

$agents = @("monitoring-agent", "analyzer-agent", "auto-response-agent", "notifier-agent", "worker")

foreach ($agent in $agents) {
    $container = docker ps --filter "name=devops-$agent" --format "{{.Status}}"

    if ($container -match "Up") {
        Write-Host "  ✓ $agent" -ForegroundColor Green -NoNewline

        # Check logs for errors
        $logs = docker logs "devops-$agent" --tail 5 2>&1
        if ($logs -match "ERROR|FATAL|Exception") {
            Write-Host " - Running with errors" -ForegroundColor Yellow
        } else {
            Write-Host " - Healthy" -ForegroundColor Green
        }
    } else {
        Write-Host "  ✗ $agent" -ForegroundColor Red -NoNewline
        Write-Host " - Not running" -ForegroundColor Red
        $allHealthy = $false
    }
}

Write-Host ""

# Check Port Accessibility
Write-Host "🌐 Dashboard Accessibility:" -ForegroundColor Yellow
Write-Host ""

$dashboards = @(
    @{Name="Approval Dashboard"; URL="http://localhost:3001"},
    @{Name="Ops Dashboard"; URL="http://localhost:3003"},
    @{Name="Grafana"; URL="http://localhost:3002"},
    @{Name="Prometheus"; URL="http://localhost:9090"},
    @{Name="RabbitMQ Management"; URL="http://localhost:15672"}
)

foreach ($dashboard in $dashboards) {
    try {
        $response = Invoke-WebRequest -Uri $dashboard.URL -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✓ $($dashboard.Name)" -ForegroundColor Green -NoNewline
        Write-Host " - $($dashboard.URL)" -ForegroundColor Gray
    } catch {
        Write-Host "  ✗ $($dashboard.Name)" -ForegroundColor Red -NoNewline
        Write-Host " - Not accessible at $($dashboard.URL)" -ForegroundColor Red
        $allHealthy = $false
    }
}

Write-Host ""

# Check RabbitMQ Queues
Write-Host "📨 Message Queue Status:" -ForegroundColor Yellow
Write-Host ""

try {
    $rabbitAuth = "devops:devops123"
    $rabbitAuthBytes = [System.Text.Encoding]::UTF8.GetBytes($rabbitAuth)
    $rabbitAuthBase64 = [System.Convert]::ToBase64String($rabbitAuthBytes)

    $headers = @{
        "Authorization" = "Basic $rabbitAuthBase64"
    }

    $queues = Invoke-RestMethod -Uri "http://localhost:15672/api/queues/%2Fdevops" -Headers $headers -TimeoutSec 5 -ErrorAction Stop

    Write-Host "  Total queues: $($queues.Count)" -ForegroundColor Cyan

    foreach ($queue in $queues) {
        $name = $queue.name
        $messages = $queue.messages

        if ($messages -gt 100) {
            Write-Host "  ⚠️  $name" -ForegroundColor Yellow -NoNewline
            Write-Host " - $messages messages (backed up)" -ForegroundColor Yellow
        } else {
            Write-Host "  ✓ $name" -ForegroundColor Green -NoNewline
            Write-Host " - $messages messages" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "  ⚠️  Could not connect to RabbitMQ API" -ForegroundColor Yellow
}

Write-Host ""

# Check Kubernetes (if applicable)
Write-Host "☸️  Kubernetes Status:" -ForegroundColor Yellow
Write-Host ""

$kindPath = ".\bin\kind.exe"
if (Test-Path $kindPath) {
    $cluster = & $kindPath get clusters 2>&1 | Select-String "devops-agent"
    if ($cluster) {
        Write-Host "  ✓ Kind cluster exists" -ForegroundColor Green

        # Check pods
        $pods = kubectl get pods -n devops-agent 2>&1
        if ($LASTEXITCODE -eq 0) {
            $runningPods = ($pods | Select-String "Running").Count
            $totalPods = ($pods | Select-String -Pattern "^\S+" | Measure-Object).Count - 1
            Write-Host "  ✓ Pods running: $runningPods / $totalPods" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Could not query Kubernetes pods" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⊘ No Kind cluster found" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⊘ Kind not installed (optional)" -ForegroundColor Gray
}

Write-Host ""

# Summary
Write-Host "============================================================================" -ForegroundColor Cyan

if ($allHealthy) {
    Write-Host "  ✅ All Systems Operational!" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Some Issues Detected" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Run the following to check logs:" -ForegroundColor Yellow
    Write-Host "  docker-compose logs -f" -ForegroundColor White
}

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Quick Actions
Write-Host "🔧 Quick Actions:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  # View all logs" -ForegroundColor White
Write-Host "  docker-compose logs -f" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Restart a service" -ForegroundColor White
Write-Host "  docker-compose restart <service-name>" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Trigger test incident" -ForegroundColor White
Write-Host "  curl -X POST http://localhost:8080/spike/cpu" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Run tests" -ForegroundColor White
Write-Host "  powershell -File run_tests.ps1" -ForegroundColor Gray
Write-Host ""
