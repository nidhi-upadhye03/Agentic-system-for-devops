# Run all tests for the DevOps Agent Platform (Windows PowerShell)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Running DevOps Agent Platform Test Suite" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$FAILED_SERVICES = @()

# Function to run tests for a service
function Run-ServiceTests {
    param(
        [string]$ServiceName,
        [string]$ServicePath
    )

    Write-Host "Testing: $ServiceName" -ForegroundColor Yellow
    Write-Host "----------------------------------------"

    if (Test-Path "$ServicePath\tests") {
        Push-Location $ServicePath
        try {
            python -m pytest tests/ -v -m unit --cov=app --cov-report=term-missing
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ $ServiceName tests passed" -ForegroundColor Green
            } else {
                Write-Host "✗ $ServiceName tests failed" -ForegroundColor Red
                $script:FAILED_SERVICES += $ServiceName
            }
        }
        catch {
            Write-Host "✗ $ServiceName tests failed with error: $_" -ForegroundColor Red
            $script:FAILED_SERVICES += $ServiceName
        }
        finally {
            Pop-Location
        }
        Write-Host ""
    } else {
        Write-Host "⊘ No tests found for $ServiceName" -ForegroundColor Gray
        Write-Host ""
    }
}

# Test Python services
Write-Host "===== Python Services =====" -ForegroundColor Cyan
Write-Host ""

Run-ServiceTests "llm-service" "services\llm-service"
Run-ServiceTests "worker-service" "services\worker-service"
Run-ServiceTests "monitoring-agent" "services\monitoring-agent"
Run-ServiceTests "analyzer-agent" "services\analyzer-agent"
Run-ServiceTests "auto-response-agent" "services\auto-response-agent"
Run-ServiceTests "memory-agent" "services\memory-agent"
Run-ServiceTests "notifier-agent" "services\notifier-agent"

# Summary
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Test Suite Summary" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

if ($FAILED_SERVICES.Count -eq 0) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Some tests failed:" -ForegroundColor Red
    foreach ($service in $FAILED_SERVICES) {
        Write-Host "  - $service" -ForegroundColor Red
    }
    exit 1
}
