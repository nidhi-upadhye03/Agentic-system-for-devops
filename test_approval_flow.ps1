# Test the complete approval flow

Write-Host "`n=============================================================" -ForegroundColor Cyan
Write-Host "TESTING COMPLETE APPROVAL WORKFLOW" -ForegroundColor Cyan
Write-Host "=============================================================`n" -ForegroundColor Cyan

# Get the latest pending approval
Write-Host "1. Fetching latest pending approval..." -ForegroundColor Yellow
$approvals = Invoke-RestMethod -Uri "http://localhost:3000/api/v1/approvals?status=pending" -Method GET -ContentType "application/json"

if ($approvals.success -and $approvals.data.Count -gt 0) {
    $approval = $approvals.data[0]
    $approvalId = $approval.id
    
    Write-Host "   ✓ Found pending approval ID: $approvalId" -ForegroundColor Green
    Write-Host "   Title: $($approval.title)" -ForegroundColor White
    Write-Host "   Status: $($approval.status)" -ForegroundColor White
    Write-Host "   Priority: $($approval.priority)" -ForegroundColor White
    Write-Host ""
    
    # Check current database state
    Write-Host "2. Current database state:" -ForegroundColor Yellow
    docker exec devops-postgres psql -U devops -d devops_db -c "SELECT id, status FROM approvals WHERE id=$approvalId;"
    Write-Host ""
    
    # Approve the request
    Write-Host "3. Approving the request..." -ForegroundColor Yellow
    $approvePayload = @{
        comment = "Approved via automated test - system verification"
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:3000/api/v1/approvals/$approvalId/approve" -Method POST -Body $approvePayload -ContentType "application/json"
        
        if ($response.success) {
            Write-Host "   ✓ Approval successful!" -ForegroundColor Green
            Write-Host "   Message: $($response.message)" -ForegroundColor White
        } else {
            Write-Host "   ✗ Approval failed: $($response.message)" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ✗ Error approving: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # Wait for auto-response to process
    Write-Host "4. Waiting 5 seconds for auto-response agent to process..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Check final database state
    Write-Host "5. Final database state:" -ForegroundColor Yellow
    docker exec devops-postgres psql -U devops -d devops_db -c "SELECT id, status, approved_at FROM approvals WHERE id=$approvalId;"
    Write-Host ""
    
    # Check auto-response logs
    Write-Host "6. Auto-response agent logs (last 10 lines):" -ForegroundColor Yellow
    docker logs devops-auto-response-agent --tail 10
    
    Write-Host "`n=============================================================" -ForegroundColor Cyan
    Write-Host "WORKFLOW TEST COMPLETE" -ForegroundColor Cyan
    Write-Host "=============================================================`n" -ForegroundColor Cyan
    
} else {
    Write-Host "   ✗ No pending approvals found" -ForegroundColor Red
    Write-Host "   Response: $($approvals | ConvertTo-Json)" -ForegroundColor White
}
