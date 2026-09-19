#!/bin/bash

###############################################################################
# [CLOUD_PROVIDER] DevOps AI System - Cleanup Script
#
# WARNING: This will DELETE ALL resources in the resource group!
#
# USAGE:
#   chmod +x cleanup-azure.sh
#   ./cleanup-azure.sh
###############################################################################

RESOURCE_GROUP="devops-ai-test-rg"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

echo ""
echo "========================================="
echo "[CLOUD_PROVIDER] DevOps AI - CLEANUP SCRIPT"
echo "========================================="
echo ""

print_warning "This script will DELETE the following:"
echo ""
echo "  • Resource Group: $RESOURCE_GROUP"
echo "  • All Container Apps (9 services)"
echo "  • Container Apps Environment"
echo "  • [CLOUD_PROVIDER] Container Registry"
echo "  • PostgreSQL Database"
echo "  • Redis Cache"
echo "  • Log Analytics Workspace"
echo "  • ALL associated data and configurations"
echo ""

print_warning "This action is IRREVERSIBLE!"
echo ""

# Check if resource group exists
RG_EXISTS=$(az group exists --name "$RESOURCE_GROUP")

if [ "$RG_EXISTS" != "true" ]; then
    print_error "Resource group '$RESOURCE_GROUP' does not exist."
    exit 1
fi

# List current resources
echo "Current resources in $RESOURCE_GROUP:"
echo ""
az resource list --resource-group "$RESOURCE_GROUP" --query "[].{Name:name, Type:type}" --output table
echo ""

# Confirmation prompt
read -p "Are you sure you want to delete ALL resources? (type 'yes' to confirm): " CONFIRMATION

if [ "$CONFIRMATION" != "yes" ]; then
    echo ""
    print_warning "Cleanup cancelled. No resources were deleted."
    exit 0
fi

echo ""
print_warning "Starting deletion process..."
echo ""

###############################################################################
# Option 1: Delete entire resource group (fast, recommended)
###############################################################################

echo "Deleting resource group: $RESOURCE_GROUP"
echo "This may take 5-10 minutes..."
echo ""

az group delete \
    --name "$RESOURCE_GROUP" \
    --yes \
    --no-wait

print_success "Deletion initiated (running in background)"
echo ""

# Monitor deletion progress
echo "Monitoring deletion progress..."
echo "You can close this script and check status later with:"
echo "  az group exists --name $RESOURCE_GROUP"
echo ""

# Wait for completion
while az group exists --name "$RESOURCE_GROUP" | grep -q "true"; do
    echo -n "."
    sleep 10
done

echo ""
echo ""
print_success "Resource group deleted successfully!"
echo ""

###############################################################################
# Verify Cleanup
###############################################################################

echo "Verifying cleanup..."
echo ""

# Check if resource group still exists
if az group exists --name "$RESOURCE_GROUP" | grep -q "false"; then
    print_success "Resource group removed"
else
    print_error "Resource group still exists"
fi

# Check for any remaining resources
REMAINING=$(az resource list --resource-group "$RESOURCE_GROUP" 2>/dev/null | grep -c "id")
if [ "$REMAINING" -eq 0 ]; then
    print_success "All resources removed"
else
    print_error "$REMAINING resources still remaining"
fi

###############################################################################
# Cost Verification
###############################################################################

echo ""
echo "========================================="
echo "Final Cost Check"
echo "========================================="
echo ""

echo "Recent costs for devops-ai resources:"
az consumption usage list \
    --start-date $(date -d '7 days ago' +%Y-%m-%d) \
    --end-date $(date +%Y-%m-%d) \
    --query "[?contains(instanceName, 'devops-ai')].{Service:instanceName, Cost:pretaxCost, Currency:currency}" \
    --output table 2>/dev/null || echo "No cost data available yet"

echo ""
print_warning "Note: Final billing may take 24-48 hours to reflect in [CLOUD_PROVIDER] portal"
echo ""

###############################################################################
# Optional: Clean up other artifacts
###############################################################################

echo "========================================="
echo "Optional Cleanup"
echo "========================================="
echo ""

read -p "Do you want to also remove local Docker images? (y/n): " CLEAN_DOCKER

if [ "$CLEAN_DOCKER" == "y" ]; then
    echo "Removing local Docker images..."
    docker rmi $(docker images | grep devopsairegistry | awk '{print $3}') 2>/dev/null || echo "No local images found"
    print_success "Local images cleaned"
fi

echo ""
read -p "Do you want to remove the deployment scripts? (y/n): " CLEAN_SCRIPTS

if [ "$CLEAN_SCRIPTS" == "y" ]; then
    echo "WARNING: This will delete:"
    echo "  - deploy-to-azure.sh"
    echo "  - verify-deployment.sh"
    echo "  - cleanup-azure.sh (this script)"
    echo "  - .env.template"
    echo "  - AZURE_DEPLOYMENT_GUIDE.md"
    echo ""
    read -p "Are you sure? (y/n): " CONFIRM_SCRIPTS

    if [ "$CONFIRM_SCRIPTS" == "y" ]; then
        rm -f deploy-to-azure.sh
        rm -f verify-deployment.sh
        rm -f .env.template
        rm -f AZURE_DEPLOYMENT_GUIDE.md
        print_success "Deployment scripts removed"
        echo ""
        print_warning "This cleanup script will now self-destruct..."
        sleep 2
        rm -f cleanup-azure.sh
    fi
fi

###############################################################################
# Summary
###############################################################################

echo ""
echo "========================================="
print_success "CLEANUP COMPLETE"
echo "========================================="
echo ""
echo "What was deleted:"
echo "  ✓ Resource Group: $RESOURCE_GROUP"
echo "  ✓ All Container Apps"
echo "  ✓ Container Apps Environment"
echo "  ✓ [CLOUD_PROVIDER] Container Registry"
echo "  ✓ PostgreSQL Database"
echo "  ✓ Redis Cache"
echo "  ✓ Log Analytics Workspace"
echo ""
echo "Next Steps:"
echo "  1. Verify costs in [CLOUD_PROVIDER] portal (Cost Management)"
echo "  2. Check for any remaining resources: az resource list"
echo "  3. If you want to redeploy, run: ./deploy-to-azure.sh"
echo ""
echo "Thank you for testing the DevOps AI system!"
echo ""
