#!/bin/bash

###############################################################################
# [CLOUD_PROVIDER] Container Apps Deployment Script - Using Docker Hub Images
# DevOps AI System - Budget: $100
#
# PREREQUISITE: Docker images must be built and pushed to Docker Hub first
# Use [SERVICE_PROVIDER] Actions workflow to build images
#
# USAGE:
# 1. Upload your devops/ folder to [CLOUD_PROVIDER] Cloud Shell
# 2. Make sure [SERVICE_PROVIDER] Actions has built all images
# 3. Run: chmod +x deploy-from-dockerhub.sh
# 4. Run: ./deploy-from-dockerhub.sh
###############################################################################

set -e  # Exit on any error

###############################################################################
# CONFIGURATION
###############################################################################

# [CLOUD_PROVIDER] Configuration
SUBSCRIPTION_ID="48ec1887-6d98-4149-9d36-356ee4b9441d"
RESOURCE_GROUP="devops-india-rg"
LOCATION="centralindia"

# Docker Hub Configuration
DOCKER_USERNAME="nidhi-upadhye03"
DOCKER_REGISTRY="docker.io"

# Database Configuration
POSTGRES_ADMIN_USER="devops"
POSTGRES_ADMIN_PASSWORD="devops123"
POSTGRES_SERVER_NAME="devops-ai-postgres"

# Redis Configuration
REDIS_NAME="devops-ai-redis"

# RabbitMQ Configuration
RABBITMQ_USER="devops"
RABBITMQ_PASSWORD="devops123"
RABBITMQ_VHOST="devops"

# LLM API Keys - EDIT THESE BEFORE DEPLOYING
OPENAI_API_KEY="${OPENAI_API_KEY:-your-openai-key-here}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-your-anthropic-key-here}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
LLM_PROVIDER="openai"

# Qdrant Cloud - EDIT THESE BEFORE DEPLOYING
QDRANT_URL="${QDRANT_URL:-your-qdrant-url-here}"
QDRANT_API_KEY="${QDRANT_API_KEY:-your-qdrant-key-here}"
QDRANT_COLLECTION_NAME="embeddings"

# Slack Configuration - EDIT THESE BEFORE DEPLOYING
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-your-slack-webhook-url-here}"
SLACK_TOKEN="${SLACK_TOKEN:-your-slack-token-here}"
SLACK_CHANNEL="#devopsalerts"

# JWT Secret
JWT_SECRET="p8K3mN9xV2qR7wL4hT6yJ1fS5dG0bM3nA8cE2vZ9uX7iO4kQ1wR6tY3"

# Container Apps Environment
CONTAINER_ENV_NAME="devops-ai-env"
LOG_WORKSPACE_NAME="devops-ai-logs"

###############################################################################
# DO NOT EDIT BELOW THIS LINE
###############################################################################

echo "========================================="
echo "[CLOUD_PROVIDER] DevOps AI Deployment Script"
echo "Using Docker Hub Images"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}âœ“ $1${NC}"
}

print_error() {
    echo -e "${RED}âœ— $1${NC}"
}

print_info() {
    echo -e "${YELLOW}â†’ $1${NC}"
}

check_result() {
    if [ $? -eq 0 ]; then
        print_success "$1"
    else
        print_error "$1 failed"
        exit 1
    fi
}

###############################################################################
# Phase 1: Initial Setup
###############################################################################

echo ""
print_info "Phase 1: Initial Setup"
echo ""

# Set subscription
print_info "Setting [CLOUD_PROVIDER] subscription..."
az account set --subscription "$SUBSCRIPTION_ID"
check_result "Subscription set"

# Create resource group
print_info "Creating resource group: $RESOURCE_GROUP..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none
check_result "Resource group created"

# Register providers
print_info "Registering [CLOUD_PROVIDER] providers..."
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider register --namespace Microsoft.DBforPostgreSQL --wait
az provider register --namespace Microsoft.Cache --wait
check_result "Providers registered"

###############################################################################
# Phase 2: Infrastructure Services
###############################################################################

echo ""
print_info "Phase 2: Infrastructure Services Setup"
echo ""

# Create PostgreSQL
print_info "Creating PostgreSQL server (this takes 5-10 minutes)..."
az postgres flexible-server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER_NAME" \
  --location "$LOCATION" \
  --admin-user "$POSTGRES_ADMIN_USER" \
  --admin-password "$POSTGRES_ADMIN_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 14 \
  --storage-size 32 \
  --public-access 0.0.0.0 \
  --yes \
  --output none
check_result "PostgreSQL server created"

# Create databases
print_info "Creating databases..."
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER_NAME" \
  --database-name devops \
  --output none
check_result "Database 'devops' created"

az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER_NAME" \
  --database-name approvals \
  --output none
check_result "Database 'approvals' created"

# Allow [CLOUD_PROVIDER] services
print_info "Configuring PostgreSQL firewall..."
az postgres flexible-server firewall-rule create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER_NAME" \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0 \
  --output none
check_result "PostgreSQL firewall configured"

# Create Redis
print_info "Creating Redis cache (this takes 5-10 minutes)..."
az redis create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REDIS_NAME" \
  --location "$LOCATION" \
  --sku Basic \
  --vm-size c0 \
  --output none
check_result "Redis cache created"

# Get Redis credentials
print_info "Retrieving Redis credentials..."
REDIS_HOST=$(az redis show --resource-group "$RESOURCE_GROUP" --name "$REDIS_NAME" --query hostName --output tsv)
REDIS_KEY=$(az redis list-keys --resource-group "$RESOURCE_GROUP" --name "$REDIS_NAME" --query primaryKey --output tsv)
check_result "Redis credentials retrieved"

###############################################################################
# Phase 3: Container Apps Environment
###############################################################################

echo ""
print_info "Phase 3: Container Apps Environment Setup"
echo ""

# Create Log Analytics workspace
print_info "Creating Log Analytics workspace..."
az monitor log-analytics workspace create \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_WORKSPACE_NAME" \
  --location "$LOCATION" \
  --output none
check_result "Log Analytics workspace created"

# Get workspace credentials
print_info "Retrieving Log Analytics credentials..."
LOG_ANALYTICS_WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_WORKSPACE_NAME" \
  --query customerId \
  --output tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_WORKSPACE_NAME" \
  --query primarySharedKey \
  --output tsv)
check_result "Log Analytics credentials retrieved"

# Create Container Apps Environment
print_info "Creating Container Apps environment..."
az containerapp env create \
  --name "$CONTAINER_ENV_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --logs-workspace-id "$LOG_ANALYTICS_WORKSPACE_ID" \
  --logs-workspace-key "$LOG_ANALYTICS_KEY" \
  --output none
check_result "Container Apps environment created"

###############################################################################
# Phase 4: Deploy RabbitMQ
###############################################################################

echo ""
print_info "Phase 4: Deploying RabbitMQ"
echo ""

az containerapp create \
  --name rabbitmq \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image docker.io/rabbitmq:3-management \
  --target-port 5672 \
  --ingress internal \
  --env-vars \
    RABBITMQ_DEFAULT_USER="$RABBITMQ_USER" \
    RABBITMQ_DEFAULT_PASS="$RABBITMQ_PASSWORD" \
    RABBITMQ_DEFAULT_VHOST="$RABBITMQ_VHOST" \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 1 \
  --output none
check_result "RabbitMQ deployed"

# Get RabbitMQ FQDN
RABBITMQ_FQDN=$(az containerapp show \
  --name rabbitmq \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)
print_success "RabbitMQ FQDN: $RABBITMQ_FQDN"

# Wait for RabbitMQ to be ready
print_info "Waiting for RabbitMQ to be ready (30 seconds)..."
sleep 30

###############################################################################
# Phase 5: Deploy Core Services from Docker Hub
###############################################################################

echo ""
print_info "Phase 5: Deploying Core Services from Docker Hub"
echo ""

# Build connection strings
POSTGRES_DEVOPS_URL="postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_SERVER_NAME}.postgres.database.azure.com:5432/devops?sslmode=require"
POSTGRES_APPROVALS_URL="postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_SERVER_NAME}.postgres.database.azure.com:5432/approvals?sslmode=require"

# Deploy LLM Service
print_info "Deploying llm-service..."
az containerapp create \
  --name llm-service \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/llm-service:latest \
  --target-port 8000 \
  --ingress internal \
  --env-vars \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    GEMINI_API_KEY="$GEMINI_API_KEY" \
    LLM_PROVIDER="$LLM_PROVIDER" \
    REDIS_HOST="$REDIS_HOST" \
    REDIS_PORT=6380 \
    REDIS_PASSWORD="$REDIS_KEY" \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 1 \
  --max-replicas 2 \
  --output none
check_result "llm-service deployed"

# Get LLM Service FQDN
LLM_SERVICE_FQDN=$(az containerapp show \
  --name llm-service \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)
LLM_SERVICE_URL="http://${LLM_SERVICE_FQDN}"

# Deploy Memory Agent
print_info "Deploying memory-agent..."
az containerapp create \
  --name memory-agent \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/memory-agent:latest \
  --env-vars \
    POSTGRES_HOST="${POSTGRES_SERVER_NAME}.postgres.database.azure.com" \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=devops \
    POSTGRES_USER="$POSTGRES_ADMIN_USER" \
    POSTGRES_PASSWORD="$POSTGRES_ADMIN_PASSWORD" \
    RABBITMQ_HOST="$RABBITMQ_FQDN" \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER="$RABBITMQ_USER" \
    RABBITMQ_PASSWORD="$RABBITMQ_PASSWORD" \
    RABBITMQ_VHOST="$RABBITMQ_VHOST" \
    QDRANT_URL="$QDRANT_URL" \
    QDRANT_API_KEY="$QDRANT_API_KEY" \
    QDRANT_COLLECTION_NAME="$QDRANT_COLLECTION_NAME" \
    LLM_SERVICE_URL="$LLM_SERVICE_URL" \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 1 \
  --max-replicas 1 \
  --output none
check_result "memory-agent deployed"

# Deploy Monitoring Agent
print_info "Deploying monitoring-agent..."
az containerapp create \
  --name monitoring-agent \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/monitoring-agent:latest \
  --env-vars \
    RABBITMQ_HOST="$RABBITMQ_FQDN" \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER="$RABBITMQ_USER" \
    RABBITMQ_PASSWORD="$RABBITMQ_PASSWORD" \
    RABBITMQ_VHOST="$RABBITMQ_VHOST" \
    PROMETHEUS_URL=http://localhost:9090 \
    K8S_IN_CLUSTER=false \
    ANOMALY_DETECTION_SENSITIVITY=2.0 \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 1 \
  --max-replicas 1 \
  --output none
check_result "monitoring-agent deployed"

# Deploy Analyzer Agent
print_info "Deploying analyzer-agent..."
az containerapp create \
  --name analyzer-agent \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/analyzer-agent:latest \
  --env-vars \
    RABBITMQ_HOST="$RABBITMQ_FQDN" \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER="$RABBITMQ_USER" \
    RABBITMQ_PASSWORD="$RABBITMQ_PASSWORD" \
    RABBITMQ_VHOST="$RABBITMQ_VHOST" \
    LLM_SERVICE_URL="$LLM_SERVICE_URL" \
    REDIS_HOST="$REDIS_HOST" \
    REDIS_PORT=6380 \
    REDIS_PASSWORD="$REDIS_KEY" \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 1 \
  --max-replicas 2 \
  --output none
check_result "analyzer-agent deployed"

# Deploy Approval Dashboard Backend
print_info "Deploying approval-dashboard-backend..."
az containerapp create \
  --name approval-dashboard-backend \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/approval-dashboard-backend:latest \
  --target-port 3000 \
  --ingress internal \
  --env-vars \
    DATABASE_URL="$POSTGRES_APPROVALS_URL" \
    JWT_SECRET="$JWT_SECRET" \
    RABBITMQ_HOST="$RABBITMQ_FQDN" \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER="$RABBITMQ_USER" \
    RABBITMQ_PASSWORD="$RABBITMQ_PASSWORD" \
    RABBITMQ_VHOST="$RABBITMQ_VHOST" \
    NODE_ENV=production \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 1 \
  --max-replicas 1 \
  --output none
check_result "approval-dashboard-backend deployed"

# Get Approval Dashboard Backend FQDN
APPROVAL_BACKEND_FQDN=$(az containerapp show \
  --name approval-dashboard-backend \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)
APPROVAL_API_URL="http://${APPROVAL_BACKEND_FQDN}"

# Deploy Auto-Response Agent
print_info "Deploying auto-response-agent..."
az containerapp create \
  --name auto-response-agent \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/auto-response-agent:latest \
  --env-vars \
    RABBITMQ_HOST="$RABBITMQ_FQDN" \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER="$RABBITMQ_USER" \
    RABBITMQ_PASSWORD="$RABBITMQ_PASSWORD" \
    RABBITMQ_VHOST="$RABBITMQ_VHOST" \
    APPROVAL_API_URL="$APPROVAL_API_URL" \
    K8S_IN_CLUSTER=false \
    AUTO_EXECUTE_THRESHOLD=0.9 \
    REQUIRES_APPROVAL_THRESHOLD=0.7 \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 1 \
  --max-replicas 1 \
  --output none
check_result "auto-response-agent deployed"

# Deploy Notifier Agent
print_info "Deploying notifier-agent..."
az containerapp create \
  --name notifier-agent \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/notifier-agent:latest \
  --env-vars \
    RABBITMQ_HOST="$RABBITMQ_FQDN" \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER="$RABBITMQ_USER" \
    RABBITMQ_PASSWORD="$RABBITMQ_PASSWORD" \
    RABBITMQ_VHOST="$RABBITMQ_VHOST" \
    SLACK_WEBHOOK_URL="$SLACK_WEBHOOK_URL" \
    SLACK_TOKEN="$SLACK_TOKEN" \
    SLACK_CHANNEL="$SLACK_CHANNEL" \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 1 \
  --max-replicas 1 \
  --output none
check_result "notifier-agent deployed"

# Deploy Approval Dashboard Frontend (public)
print_info "Deploying approval-dashboard-frontend..."
az containerapp create \
  --name approval-dashboard-frontend \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/approval-dashboard-frontend:latest \
  --target-port 80 \
  --ingress external \
  --env-vars \
    REACT_APP_API_URL="$APPROVAL_API_URL" \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 1 \
  --max-replicas 2 \
  --output none
check_result "approval-dashboard-frontend deployed"

# Get Frontend URL
FRONTEND_FQDN=$(az containerapp show \
  --name approval-dashboard-frontend \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

# Deploy Test App (for chaos engineering)
print_info "Deploying test-app..."
az containerapp create \
  --name test-app \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image ${DOCKER_USERNAME}/test-app:latest \
  --target-port 8080 \
  --ingress internal \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 1 \
  --output none
check_result "test-app deployed"

# Get Test App FQDN
TEST_APP_FQDN=$(az containerapp show \
  --name test-app \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

###############################################################################
# Deployment Complete
###############################################################################

echo ""
echo "========================================="
print_success "DEPLOYMENT COMPLETE!"
echo "========================================="
echo ""
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""
echo "Services Deployed:"
echo "  âœ“ RabbitMQ (message broker)"
echo "  âœ“ PostgreSQL (database)"
echo "  âœ“ Redis (cache)"
echo "  âœ“ monitoring-agent"
echo "  âœ“ analyzer-agent"
echo "  âœ“ auto-response-agent"
echo "  âœ“ notifier-agent"
echo "  âœ“ memory-agent"
echo "  âœ“ llm-service"
echo "  âœ“ approval-dashboard-backend"
echo "  âœ“ approval-dashboard-frontend"
echo "  âœ“ test-app (chaos engineering)"
echo ""
echo "Access URLs:"
echo "  Approval Dashboard: https://$FRONTEND_FQDN"
echo "  LLM Service (internal): $LLM_SERVICE_URL"
echo "  Test App (internal): http://$TEST_APP_FQDN"
echo ""
echo "Test App Endpoints (trigger chaos for testing):"
echo "  POST http://$TEST_APP_FQDN/trigger-cpu - High CPU usage (80%+ for 2 min)"
echo "  POST http://$TEST_APP_FQDN/trigger-memory - Memory leak (50MB/10s)"
echo "  POST http://$TEST_APP_FQDN/trigger-crash - Crash pod (restart test)"
echo "  POST http://$TEST_APP_FQDN/trigger-errors - HTTP 500 errors (50% rate)"
echo "  POST http://$TEST_APP_FQDN/reset - Stop all chaos scenarios"
echo "  GET  http://$TEST_APP_FQDN/status - Current chaos state"
echo "  GET  http://$TEST_APP_FQDN/metrics - Prometheus metrics"
echo ""
echo "Next Steps:"
echo "  1. Open the Approval Dashboard: https://$FRONTEND_FQDN"
echo "  2. Check logs: az containerapp logs show --name monitoring-agent --resource-group $RESOURCE_GROUP --follow"
echo "  3. Monitor costs: az consumption usage list"
echo ""
echo "Cleanup (when done testing):"
echo "  az group delete --name $RESOURCE_GROUP --yes --no-wait"
echo ""
echo "Estimated monthly cost: \$51-66"
echo "========================================="

