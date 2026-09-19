# ============================================================================
# DevOps Agent Platform - Local Shutdown Script (Windows PowerShell)
# ============================================================================
# This script stops all services for local deployment
# Usage: powershell -File stop.ps1

param(
    [switch]$RemoveData = $false,
    [switch]$WithKubernetes = $false
)

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Stopping DevOps Agent Platform - Local Deployment" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Stop Docker Compose services
Write-Host "[1/3] Stopping Docker Compose services..." -ForegroundColor Yellow

if ($RemoveData) {
    Write-Host "  ⚠️  Warning: This will DELETE all data (databases, queues, etc.)" -ForegroundColor Red
    Write-Host "  Press Ctrl+C to cancel, or Enter to continue..." -ForegroundColor Yellow
    Read-Host
    docker-compose down -v
    Write-Host "✓ Services stopped and data removed" -ForegroundColor Green
} else {
    docker-compose down
    Write-Host "✓ Services stopped (data preserved)" -ForegroundColor Green
}
Write-Host ""

# Stop Kubernetes
if ($WithKubernetes) {
    Write-Host "[2/3] Stopping Kubernetes cluster..." -ForegroundColor Yellow

    $kindPath = ".\bin\kind.exe"
    if (Test-Path $kindPath) {
        & $kindPath delete cluster --name devops-agent
        Write-Host "✓ Kubernetes cluster deleted" -ForegroundColor Green
    } else {
        Write-Host "⊘ Kind not found, skipping Kubernetes cleanup" -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host "[2/3] Kubernetes cleanup skipped (use -WithKubernetes to enable)" -ForegroundColor Gray
    Write-Host ""
}

# Show status
Write-Host "[3/3] Verifying shutdown..." -ForegroundColor Yellow

$runningContainers = docker ps --filter "name=devops-*" --format "{{.Names}}"
if ($runningContainers) {
    Write-Host "⚠️  Some containers are still running:" -ForegroundColor Yellow
    $runningContainers | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
} else {
    Write-Host "✓ All services stopped" -ForegroundColor Green
}
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Shutdown Complete!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

if (-not $RemoveData) {
    Write-Host "💡 Your data is preserved. To start again:" -ForegroundColor Yellow
    Write-Host "   powershell -File start.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "   To remove all data:" -ForegroundColor Yellow
    Write-Host "   powershell -File stop.ps1 -RemoveData" -ForegroundColor White
} else {
    Write-Host "🗑️  All data has been removed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   To start fresh:" -ForegroundColor Yellow
    Write-Host "   powershell -File start.ps1" -ForegroundColor White
}
Write-Host ""
