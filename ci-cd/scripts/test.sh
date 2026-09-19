#!/bin/bash

################################################################################
# Test Execution Script
# Description: Runs all types of tests with reporting
# Usage: ./test.sh [test-type] [options]
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_TYPE="${TEST_TYPE:-all}"
ENVIRONMENT="${NODE_ENV:-test}"
COVERAGE="${COVERAGE:-false}"
PARALLEL="${PARALLEL:-false}"
VERBOSE="${VERBOSE:-false}"

# Function to print colored messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run tests for the application

OPTIONS:
    -t, --type TYPE             Test type (unit|integration|e2e|smoke|all) [default: all]
    -e, --environment ENV       Environment (test|dev|staging) [default: test]
    -c, --coverage              Generate coverage report
    -p, --parallel              Run tests in parallel
    -v, --verbose               Verbose output
    -w, --watch                 Watch mode
    --bail                      Stop on first failure
    --timeout SECONDS           Test timeout in seconds
    -h, --help                  Display this help message

EXAMPLES:
    $0 --type unit --coverage
    $0 --type integration --environment staging
    $0 -t e2e -v
    $0 --type all --parallel --coverage
EOF
    exit 1
}

# Parse command line arguments
WATCH=false
BAIL=false
TIMEOUT="300"

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -w|--watch)
            WATCH=true
            shift
            ;;
        --bail)
            BAIL=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if dependencies are installed
check_dependencies() {
    log_info "Checking dependencies..."

    if [ ! -d "node_modules" ]; then
        log_warning "node_modules not found. Installing dependencies..."
        npm ci
    fi
}

# Run unit tests
run_unit_tests() {
    log_info "Running unit tests..."

    local cmd="npm run test:unit"
    local opts=()

    if [ "$COVERAGE" = true ]; then
        opts+=("-- --coverage")
    fi

    if [ "$VERBOSE" = true ]; then
        opts+=("--verbose")
    fi

    if [ "$WATCH" = true ]; then
        opts+=("--watch")
    fi

    if [ "$BAIL" = true ]; then
        opts+=("--bail")
    fi

    if [ "$PARALLEL" = true ]; then
        opts+=("--maxWorkers=4")
    fi

    if eval "$cmd ${opts[*]}" 2>&1; then
        log_success "Unit tests passed"
        return 0
    else
        log_error "Unit tests failed"
        return 1
    fi
}

# Run integration tests
run_integration_tests() {
    log_info "Running integration tests..."

    # Setup test environment
    export NODE_ENV="${ENVIRONMENT}"

    # Start test database if needed
    if command -v docker-compose &> /dev/null; then
        log_info "Starting test infrastructure..."
        docker-compose -f docker-compose.test.yml up -d || true
        sleep 5
    fi

    local cmd="npm run test:integration"
    local opts=()

    if [ "$COVERAGE" = true ]; then
        opts+=("-- --coverage")
    fi

    if [ "$VERBOSE" = true ]; then
        opts+=("--verbose")
    fi

    if [ "$TIMEOUT" ]; then
        opts+=("--testTimeout=${TIMEOUT}000")
    fi

    if eval "$cmd ${opts[*]}" 2>&1; then
        log_success "Integration tests passed"
        cleanup_test_infrastructure
        return 0
    else
        log_error "Integration tests failed"
        cleanup_test_infrastructure
        return 1
    fi
}

# Run end-to-end tests
run_e2e_tests() {
    log_info "Running end-to-end tests..."

    export NODE_ENV="${ENVIRONMENT}"

    # Check if application is running
    if [ "$ENVIRONMENT" = "test" ]; then
        log_info "Starting application for e2e tests..."
        npm run start:test &
        APP_PID=$!
        sleep 10
    fi

    local cmd="npm run test:e2e"
    local opts=()

    if [ "$VERBOSE" = true ]; then
        opts+=("--verbose")
    fi

    if [ "$TIMEOUT" ]; then
        opts+=("--testTimeout=${TIMEOUT}000")
    fi

    if eval "$cmd ${opts[*]}" 2>&1; then
        log_success "E2E tests passed"
        [ -n "${APP_PID:-}" ] && kill "$APP_PID" 2>/dev/null || true
        return 0
    else
        log_error "E2E tests failed"
        [ -n "${APP_PID:-}" ] && kill "$APP_PID" 2>/dev/null || true
        return 1
    fi
}

# Run smoke tests
run_smoke_tests() {
    log_info "Running smoke tests..."

    export NODE_ENV="${ENVIRONMENT}"

    local cmd="npm run test:smoke"

    if [ ! "$(npm run | grep test:smoke)" ]; then
        log_warning "Smoke tests not configured, skipping..."
        return 0
    fi

    if eval "$cmd" 2>&1; then
        log_success "Smoke tests passed"
        return 0
    else
        log_error "Smoke tests failed"
        return 1
    fi
}

# Run linting
run_lint() {
    log_info "Running linter..."

    if npm run lint 2>&1; then
        log_success "Linting passed"
        return 0
    else
        log_error "Linting failed"
        return 1
    fi
}

# Run type checking
run_type_check() {
    log_info "Running type check..."

    if [ -f "tsconfig.json" ]; then
        if npx tsc --noEmit 2>&1; then
            log_success "Type check passed"
            return 0
        else
            log_error "Type check failed"
            return 1
        fi
    else
        log_info "TypeScript not configured, skipping type check"
        return 0
    fi
}

# Cleanup test infrastructure
cleanup_test_infrastructure() {
    if command -v docker-compose &> /dev/null; then
        log_info "Cleaning up test infrastructure..."
        docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true
    fi
}

# Generate coverage report
generate_coverage_report() {
    if [ "$COVERAGE" = true ]; then
        log_info "Generating coverage report..."

        if [ -d "coverage" ]; then
            log_info "Coverage summary:"
            cat coverage/coverage-summary.json 2>/dev/null || echo "Coverage summary not found"

            log_info "HTML report available at: coverage/lcov-report/index.html"
        else
            log_warning "No coverage directory found"
        fi
    fi
}

# Main test execution
main() {
    log_info "Starting test execution..."
    log_info "Test type: $TEST_TYPE"
    log_info "Environment: $ENVIRONMENT"
    log_info "Coverage: $COVERAGE"
    log_info "Parallel: $PARALLEL"
    echo ""

    check_dependencies

    local failed_tests=()

    # Run tests based on type
    case "$TEST_TYPE" in
        unit)
            run_unit_tests || failed_tests+=("unit")
            ;;
        integration)
            run_integration_tests || failed_tests+=("integration")
            ;;
        e2e)
            run_e2e_tests || failed_tests+=("e2e")
            ;;
        smoke)
            run_smoke_tests || failed_tests+=("smoke")
            ;;
        all)
            log_info "Running all tests..."
            echo ""

            run_lint || failed_tests+=("lint")
            echo ""

            run_type_check || failed_tests+=("type-check")
            echo ""

            run_unit_tests || failed_tests+=("unit")
            echo ""

            run_integration_tests || failed_tests+=("integration")
            echo ""

            run_smoke_tests || failed_tests+=("smoke")
            echo ""
            ;;
        *)
            log_error "Invalid test type: $TEST_TYPE"
            usage
            ;;
    esac

    # Generate coverage report
    generate_coverage_report

    # Summary
    echo ""
    log_info "========================================="
    log_info "Test Execution Summary"
    log_info "========================================="

    if [ ${#failed_tests[@]} -eq 0 ]; then
        log_success "All tests passed!"
        exit 0
    else
        log_error "Failed tests: ${failed_tests[*]}"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    log_warning "Tests interrupted"
    cleanup_test_infrastructure
    exit 130
}

# Trap SIGINT (Ctrl+C) and EXIT
trap cleanup INT EXIT

# Run main function
main
