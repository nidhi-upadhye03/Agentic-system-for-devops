#!/bin/bash

# GitHub Codespaces Setup Script
# This script runs automatically after the devcontainer is created

set -e

echo "=================================================="
echo "  AI-Driven Hybrid Kubernetes System Setup"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Navigate to devops directory
cd /workspace/devops || {
    print_error "devops directory not found"
    exit 1
}

# Step 1: Install Python dependencies for LLM Service
echo ""
echo "Step 1: Installing Python dependencies for LLM Service..."
cd services/llm-service
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    print_success "Python dependencies installed"
else
    print_warning "requirements.txt not found"
fi
cd /workspace/devops

# Step 2: Install Node.js dependencies for Approval Backend
echo ""
echo "Step 2: Installing Node.js dependencies for Approval Backend..."
cd services/approval-dashboard/backend
if [ -f "package.json" ]; then
    npm install --silent
    print_success "Backend Node.js dependencies installed"
else
    print_warning "Backend package.json not found"
fi
cd /workspace/devops

# Step 3: Install Node.js dependencies for Approval Frontend
echo ""
echo "Step 3: Installing Node.js dependencies for Approval Frontend..."
cd services/approval-dashboard/frontend
if [ -f "package.json" ]; then
    npm install --silent
    print_success "Frontend Node.js dependencies installed"
else
    print_warning "Frontend package.json not found"
fi
cd /workspace/devops

# Step 4: Install Python dependencies for Worker Service
echo ""
echo "Step 4: Installing Python dependencies for Worker Service..."
cd services/worker-service
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    print_success "Worker Service dependencies installed"
else
    print_warning "Worker Service requirements.txt not found"
fi
cd /workspace/devops

# Step 5: Create .env file from template if it doesn't exist
echo ""
echo "Step 5: Setting up environment variables..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created from template"
        print_warning "IMPORTANT: Update .env with your API keys!"
    else
        print_warning ".env.example not found, skipping .env creation"
    fi
else
    print_success ".env file already exists"
fi

# Step 6: Wait for services to be ready
echo ""
echo "Step 6: Waiting for services to start..."

# Function to wait for a service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            print_success "$service_name is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done

    print_warning "$service_name not ready after ${max_attempts} attempts"
    return 1
}

# Wait for PostgreSQL
wait_for_service localhost 5432 "PostgreSQL"

# Wait for Redis
wait_for_service localhost 6379 "Redis"

# Wait for RabbitMQ
wait_for_service localhost 5672 "RabbitMQ"

# Wait for Qdrant
wait_for_service localhost 6333 "Qdrant"

# Step 7: Initialize RabbitMQ queues
echo ""
echo "Step 7: Initializing RabbitMQ queues..."
if [ -f "infrastructure/rabbitmq/init-queues.sh" ]; then
    bash infrastructure/rabbitmq/init-queues.sh || print_warning "RabbitMQ initialization script failed"
    print_success "RabbitMQ queues initialized"
else
    print_warning "RabbitMQ initialization script not found"
fi

# Step 8: Verify database schema
echo ""
echo "Step 8: Verifying database schema..."
if command -v psql &> /dev/null; then
    PGPASSWORD=devops123 psql -h localhost -U devops -d devops_db -c "SELECT version();" &>/dev/null && \
        print_success "Database connection verified" || \
        print_warning "Database connection failed"
else
    print_warning "psql not found, skipping database verification"
fi

# Step 9: Display service URLs
echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "Service URLs (will be forwarded by Codespaces):"
echo "  • Approval Frontend:    http://localhost:3001"
echo "  • Approval Backend:     http://localhost:3000"
echo "  • LLM Service API:      http://localhost:8000"
echo "  • LLM Service Docs:     http://localhost:8000/docs"
echo "  • RabbitMQ Management:  http://localhost:15672"
echo "  • Grafana:              http://localhost:3002"
echo "  • Prometheus:           http://localhost:9090"
echo ""
echo "Database Services:"
echo "  • PostgreSQL:           localhost:5432"
echo "  • Redis:                localhost:6379"
echo "  • RabbitMQ:             localhost:5672"
echo "  • Qdrant:               localhost:6333"
echo ""
echo "Default Credentials:"
echo "  • Admin:     admin@devops.local / Admin@123"
echo "  • Approver:  approver@devops.local / Approver@123"
echo "  • Developer: developer@devops.local / Developer@123"
echo "  • Viewer:    viewer@devops.local / Viewer@123"
echo ""
echo "Next Steps:"
echo "  1. Update .env with your API keys:"
echo "     • OPENAI_API_KEY"
echo "     • ANTHROPIC_API_KEY (optional)"
echo ""
echo "  2. Start services:"
echo "     cd /workspace/devops"
echo "     docker-compose up -d"
echo ""
echo "  3. Test LLM Service:"
echo "     cd /workspace/devops/services/llm-service"
echo "     python test_complete.py"
echo ""
echo "  4. Access the dashboard:"
echo "     Open http://localhost:3001 in your browser"
echo ""
echo "=================================================="

print_success "Setup completed successfully!"
