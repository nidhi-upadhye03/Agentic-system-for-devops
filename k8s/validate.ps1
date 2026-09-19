# PowerShell Validation Script for Windows
# This script validates the Kubernetes manifests before deployment

$ErrorActionPreference = "Continue"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "K8s Manifest Validation Script" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$script:FailedCount = 0

# Check if kubectl is installed
try {
    kubectl version --client --short | Out-Null
    Write-Host "✓ kubectl is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: kubectl is not installed" -ForegroundColor Red
    exit 1
}

# Check if kustomize is available
try {
    kubectl kustomize --help | Out-Null
    Write-Host "✓ kustomize is available" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: kustomize is not available in kubectl" -ForegroundColor Red
    exit 1
}

# Function to validate kustomization
function Validate-Kustomization {
    param([string]$env)

    Write-Host ""
    Write-Host "Validating $env environment..." -ForegroundColor Yellow

    # Check if kustomization builds
    try {
        kubectl kustomize "overlays/$env/" | Out-Null
        Write-Host "✓ $env kustomization builds successfully" -ForegroundColor Green
    } catch {
        Write-Host "✗ $env kustomization build failed" -ForegroundColor Red
        kubectl kustomize "overlays/$env/"
        $script:FailedCount++
        return
    }

    # Validate generated manifests
    try {
        kubectl kustomize "overlays/$env/" | kubectl apply --dry-run=client -f - | Out-Null
        Write-Host "✓ $env manifests are valid" -ForegroundColor Green
    } catch {
        Write-Host "✗ $env manifests validation failed" -ForegroundColor Red
        kubectl kustomize "overlays/$env/" | kubectl apply --dry-run=client -f -
        $script:FailedCount++
        return
    }
}

# Validate base
Write-Host ""
Write-Host "Validating base manifests..." -ForegroundColor Yellow
try {
    kubectl kustomize "base/" | Out-Null
    Write-Host "✓ Base kustomization builds successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Base kustomization build failed" -ForegroundColor Red
    kubectl kustomize "base/"
    exit 1
}

# Validate each environment
$environments = @("dev", "staging", "prod")
foreach ($env in $environments) {
    Validate-Kustomization -env $env
}

# Check for common issues
Write-Host ""
Write-Host "Checking for common issues..." -ForegroundColor Yellow

# Check for default secrets
if (Select-String -Path "base/secrets.yaml" -Pattern "changeme-" -Quiet) {
    Write-Host "⚠  Warning: Default secrets detected in base/secrets.yaml" -ForegroundColor Yellow
    Write-Host "   Please update secrets before deploying to production!" -ForegroundColor Yellow
}

# Check for placeholder image names
$hasPlaceholders = $false
Get-ChildItem -Path . -Filter "kustomization.yaml" -Recurse | ForEach-Object {
    if (Select-String -Path $_.FullName -Pattern "your-registry" -Quiet) {
        $hasPlaceholders = $true
    }
}
if ($hasPlaceholders) {
    Write-Host "⚠  Warning: Placeholder registry names detected" -ForegroundColor Yellow
    Write-Host "   Please update image registry before deployment!" -ForegroundColor Yellow
}

# Check for example domains
if (Test-Path "overlays/prod/ingress-patch.yaml") {
    if (Select-String -Path "overlays/prod/ingress-patch.yaml" -Pattern "example.com" -Quiet) {
        Write-Host "⚠  Warning: Example domains detected in production ingress" -ForegroundColor Yellow
        Write-Host "   Please update domains before deploying to production!" -ForegroundColor Yellow
    }
}

# Summary
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
if ($script:FailedCount -eq 0) {
    Write-Host "✓ All validations passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Update secrets in base/secrets.yaml"
    Write-Host "2. Update image registry in kustomization.yaml files"
    Write-Host "3. Update production domains in overlays/prod/ingress-patch.yaml"
    Write-Host "4. Deploy: kubectl apply -k overlays/<env>/"
    exit 0
} else {
    Write-Host "✗ $script:FailedCount validation(s) failed" -ForegroundColor Red
    Write-Host "Please fix the errors above before deploying" -ForegroundColor Red
    exit 1
}
