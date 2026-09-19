#!/bin/bash

###############################################################################
# [CLOUD_PROVIDER] DevOps AI System - Verification & Monitoring Script
#
# USAGE:
#   chmod +x verify-deployment.sh
#   ./verify-deployment.sh
###############################################################################

# Configuration
RESOURCE_GROUP="devops-ai-test-rg"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

###############################################################################
# Check All Services Status
###############################################################################

print_header "1. Container Apps Status"

SERVICES=(
    "rabbitmq"
    "monitoring-agent"
    "analyzer-agent"
    "auto-response-agent"
    "notifier-agent"
    "memory-agent"
    "llm-service"
    "approval-dashboard-backend"
    "approval-dashboard-frontend"
)

for SERVICE in "${SERVICES[@]}"; do
    STATUS=$(az containerapp show \
        --name "$SERVICE" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.runningStatus" \
        --output tsv 2>/dev/null)

    if [ "$STATUS" == "Running" ]; then
        print_success "$SERVICE: $STATUS"
    else
        print_error "$SERVICE: $STATUS"
    fi
done

###############################################################################
# Get Service URLs
###############################################################################

print_header "2. Service URLs"

# Frontend (public)
FRONTEND_URL=$(az containerapp show \
    --name approval-dashboard-frontend \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv 2>/dev/null)

if [ -n "$FRONTEND_URL" ]; then
    print_info "Approval Dashboard (Public): https://$FRONTEND_URL"
fi

# LLM Service (internal)
LLM_URL=$(az containerapp show \
    --name llm-service \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv 2>/dev/null)

if [ -n "$LLM_URL" ]; then
    print_info "LLM Service (Internal): http://$LLM_URL"
fi

# RabbitMQ (internal)
RABBITMQ_URL=$(az containerapp show \
    --name rabbitmq \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv 2>/dev/null)

if [ -n "$RABBITMQ_URL" ]; then
    print_info "RabbitMQ (Internal): http://$RABBITMQ_URL"
fi

###############################################################################
# Check Database Status
###############################################################################

print_header "3. Database Status"

# PostgreSQL
PG_STATUS=$(az postgres flexible-server show \
    --resource-group "$RESOURCE_GROUP" \
    --name devops-ai-postgres \
    --query state \
    --output tsv 2>/dev/null)

if [ "$PG_STATUS" == "Ready" ]; then
    print_success "PostgreSQL: $PG_STATUS"
else
    print_error "PostgreSQL: $PG_STATUS"
fi

# Redis
REDIS_STATUS=$(az redis show \
    --resource-group "$RESOURCE_GROUP" \
    --name devops-ai-redis \
    --query provisioningState \
    --output tsv 2>/dev/null)

if [ "$REDIS_STATUS" == "Succeeded" ]; then
    print_success "Redis: $REDIS_STATUS"
else
    print_error "Redis: $REDIS_STATUS"
fi

###############################################################################
# Check Recent Logs
###############################################################################

print_header "4. Recent Logs (Last 10 lines per service)"

for SERVICE in "monitoring-agent" "analyzer-agent" "llm-service"; do
    echo ""
    print_info "$SERVICE logs:"
    az containerapp logs show \
        --name "$SERVICE" \
        --resource-group "$RESOURCE_GROUP" \
        --tail 10 \
        --output table 2>/dev/null || print_error "Could not fetch logs for $SERVICE"
done

###############################################################################
# Check Resource Usage
###############################################################################

print_header "5. Resource Metrics"

for SERVICE in "${SERVICES[@]}"; do
    REPLICAS=$(az containerapp show \
        --name "$SERVICE" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.template.scale.minReplicas" \
        --output tsv 2>/dev/null)

    CPU=$(az containerapp show \
        --name "$SERVICE" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.template.containers[0].resources.cpu" \
        --output tsv 2>/dev/null)

    MEMORY=$(az containerapp show \
        --name "$SERVICE" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.template.containers[0].resources.memory" \
        --output tsv 2>/dev/null)

    echo "$SERVICE: $REPLICAS replicas, $CPU CPU, $MEMORY RAM"
done

###############################################################################
# Cost Monitoring
###############################################################################

print_header "6. Cost Analysis"

print_info "Checking current costs..."
echo ""

# Get cost for last 7 days
az consumption usage list \
    --start-date $(date -d '7 days ago' +%Y-%m-%d) \
    --end-date $(date +%Y-%m-%d) \
    --query "[?contains(instanceName, 'devops-ai')].{Service:instanceName, Cost:pretaxCost, Currency:currency}" \
    --output table 2>/dev/null || print_error "Could not fetch cost data"

###############################################################################
# Health Checks
###############################################################################

print_header "7. Health Endpoint Tests"

# Test LLM Service health (only if accessible from current context)
print_info "Testing LLM service health endpoint..."
if [ -n "$LLM_URL" ]; then
    # Note: This will only work if running from within [CLOUD_PROVIDER] environment
    print_info "LLM Health URL: http://$LLM_URL/health (internal only)"
else
    print_error "LLM service URL not found"
fi

###############################################################################
# Troubleshooting Commands
###############################################################################

print_header "8. Useful Commands for Troubleshooting"

echo "View logs (follow mode):"
echo "  az containerapp logs show --name <SERVICE_NAME> --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "Restart a service:"
echo "  az containerapp revision restart --name <SERVICE_NAME> --resource-group $RESOURCE_GROUP"
echo ""
echo "Scale a service:"
echo "  az containerapp update --name <SERVICE_NAME> --resource-group $RESOURCE_GROUP --min-replicas 0 --max-replicas 2"
echo ""
echo "Get service details:"
echo "  az containerapp show --name <SERVICE_NAME> --resource-group $RESOURCE_GROUP"
echo ""
echo "Test RabbitMQ connectivity:"
echo "  az containerapp exec --name rabbitmq --resource-group $RESOURCE_GROUP --command /bin/bash"
echo ""
echo "View PostgreSQL databases:"
echo "  az postgres flexible-server db list --resource-group $RESOURCE_GROUP --server-name devops-ai-postgres"
echo ""
echo "Check Redis connection:"
echo "  az redis show --resource-group $RESOURCE_GROUP --name devops-ai-redis"
echo ""

###############################################################################
# Summary
###############################################################################

print_header "Verification Complete"

echo "Next Steps:"
echo "  1. Open Approval Dashboard: https://$FRONTEND_URL"
echo "  2. Check if Slack notifications are working"
echo "  3. Trigger a test incident in monitoring-agent"
echo "  4. Watch logs to see event flow"
echo ""
echo "To monitor specific service:"
echo "  az containerapp logs show --name <SERVICE_NAME> --resource-group $RESOURCE_GROUP --follow"
echo ""
