#!/bin/bash
# Kubernetes Manifest Validation Script
# This script validates the Kubernetes manifests before deployment

set -e

echo "================================"
echo "K8s Manifest Validation Script"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}ERROR: kubectl is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} kubectl is installed"

# Check if kustomize is available
if ! kubectl kustomize --help &> /dev/null; then
    echo -e "${RED}ERROR: kustomize is not available in kubectl${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} kustomize is available"

# Function to validate kustomization
validate_kustomization() {
    local env=$1
    echo ""
    echo "Validating $env environment..."

    # Check if kustomization builds
    if kubectl kustomize overlays/$env/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $env kustomization builds successfully"
    else
        echo -e "${RED}✗${NC} $env kustomization build failed"
        kubectl kustomize overlays/$env/
        return 1
    fi

    # Validate generated manifests
    if kubectl kustomize overlays/$env/ | kubectl apply --dry-run=client -f - > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $env manifests are valid"
    else
        echo -e "${RED}✗${NC} $env manifests validation failed"
        kubectl kustomize overlays/$env/ | kubectl apply --dry-run=client -f -
        return 1
    fi

    return 0
}

# Validate base
echo ""
echo "Validating base manifests..."
if kubectl kustomize base/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Base kustomization builds successfully"
else
    echo -e "${RED}✗${NC} Base kustomization build failed"
    kubectl kustomize base/
    exit 1
fi

# Validate each environment
ENVS=("dev" "staging" "prod")
FAILED=0

for env in "${ENVS[@]}"; do
    if ! validate_kustomization $env; then
        FAILED=1
    fi
done

# Check for common issues
echo ""
echo "Checking for common issues..."

# Check for default secrets
if grep -r "changeme-" base/secrets.yaml > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC}  Warning: Default secrets detected in base/secrets.yaml"
    echo "   Please update secrets before deploying to production!"
fi

# Check for placeholder image names
if grep -r "your-registry" base/kustomization.yaml overlays/*/kustomization.yaml > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC}  Warning: Placeholder registry names detected"
    echo "   Please update image registry before deployment!"
fi

# Check for example domains
if grep -r "example.com" overlays/prod/ingress-patch.yaml > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC}  Warning: Example domains detected in production ingress"
    echo "   Please update domains before deploying to production!"
fi

# Summary
echo ""
echo "================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All validations passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Update secrets in base/secrets.yaml"
    echo "2. Update image registry in kustomization.yaml files"
    echo "3. Update production domains in overlays/prod/ingress-patch.yaml"
    echo "4. Deploy: kubectl apply -k overlays/<env>/"
    exit 0
else
    echo -e "${RED}✗ Some validations failed${NC}"
    echo "Please fix the errors above before deploying"
    exit 1
fi
