#!/bin/bash

# Approval Dashboard Backend - Setup Script
# This script sets up the complete backend environment

set -e  # Exit on error

echo "=================================================="
echo "  Approval Dashboard Backend - Setup Script"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if Node.js is installed
check_node() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18 or higher."
        exit 1
    fi

    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        print_error "Node.js version must be 18 or higher. Current version: $(node -v)"
        exit 1
    fi

    print_success "Node.js $(node -v) is installed"
}

# Check if PostgreSQL is installed
check_postgres() {
    if ! command -v psql &> /dev/null; then
        print_error "PostgreSQL is not installed. Please install PostgreSQL 12 or higher."
        exit 1
    fi

    print_success "PostgreSQL is installed"
}

# Install dependencies
install_dependencies() {
    print_info "Installing dependencies..."
    npm install
    print_success "Dependencies installed"
}

# Setup environment file
setup_env() {
    if [ ! -f .env ]; then
        print_info "Creating .env file from .env.example..."
        cp .env.example .env
        print_success ".env file created"
        print_info "Please edit .env file with your configuration before proceeding."

        read -p "Press Enter to continue after editing .env file..."
    else
        print_success ".env file already exists"
    fi
}

# Create database
create_database() {
    print_info "Creating PostgreSQL database..."

    # Load DB credentials from .env
    source .env

    # Check if database exists
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
        print_info "Database '$DB_NAME' already exists"
    else
        # Create database
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -c "CREATE DATABASE $DB_NAME;"
        print_success "Database '$DB_NAME' created"
    fi
}

# Run migrations
run_migrations() {
    print_info "Running database migrations..."
    npm run migrate
    print_success "Database migrations completed"
}

# Start server
start_server() {
    print_info "Starting server..."

    echo ""
    echo "=================================================="
    echo "  Server is starting..."
    echo "=================================================="
    echo ""
    print_success "Backend is ready!"
    echo ""
    print_info "Default credentials:"
    echo "  Admin: admin@approvaldashboard.com / Admin@123"
    echo ""
    print_info "API URL: http://localhost:5000/api/v1"
    print_info "Health Check: http://localhost:5000/health"
    echo ""
    echo "=================================================="
    echo ""

    npm run dev
}

# Main setup flow
main() {
    echo ""
    print_info "Starting setup process..."
    echo ""

    # Step 1: Check prerequisites
    print_info "Step 1: Checking prerequisites..."
    check_node
    check_postgres
    echo ""

    # Step 2: Install dependencies
    print_info "Step 2: Installing dependencies..."
    install_dependencies
    echo ""

    # Step 3: Setup environment
    print_info "Step 3: Setting up environment..."
    setup_env
    echo ""

    # Step 4: Create database
    print_info "Step 4: Creating database..."
    create_database
    echo ""

    # Step 5: Run migrations
    print_info "Step 5: Running migrations..."
    run_migrations
    echo ""

    # Step 6: Start server
    print_info "Step 6: Starting server..."
    start_server
}

# Run main function
main
