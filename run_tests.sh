#!/usr/bin/env bash
# Run all tests for the DevOps Agent Platform

set -e

echo "================================================"
echo "Running DevOps Agent Platform Test Suite"
echo "================================================"
echo ""

FAILED_SERVICES=()
TOTAL_COVERAGE=0
SERVICE_COUNT=0

# Function to run tests for a service
run_service_tests() {
    local service=$1
    local service_path=$2

    echo "Testing: $service"
    echo "----------------------------------------"

    if [ -d "$service_path/tests" ]; then
        cd "$service_path"
        if pytest tests/ -v -m unit --cov=app --cov-report=term-missing 2>&1 | tee test_output.txt; then
            echo "✓ $service tests passed"
        else
            echo "✗ $service tests failed"
            FAILED_SERVICES+=("$service")
        fi
        cd - > /dev/null
        echo ""
    else
        echo "⊘ No tests found for $service"
        echo ""
    fi
}

# Test Python services
echo "===== Python Services ====="
echo ""

run_service_tests "llm-service" "services/llm-service"
run_service_tests "worker-service" "services/worker-service"
run_service_tests "monitoring-agent" "services/monitoring-agent"
run_service_tests "analyzer-agent" "services/analyzer-agent"
run_service_tests "auto-response-agent" "services/auto-response-agent"
run_service_tests "memory-agent" "services/memory-agent"
run_service_tests "notifier-agent" "services/notifier-agent"

# Summary
echo "================================================"
echo "Test Suite Summary"
echo "================================================"
echo ""

if [ ${#FAILED_SERVICES[@]} -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Some tests failed:"
    for service in "${FAILED_SERVICES[@]}"; do
        echo "  - $service"
    done
    exit 1
fi
