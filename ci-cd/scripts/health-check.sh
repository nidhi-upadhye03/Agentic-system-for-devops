#!/bin/bash

################################################################################
# Health Check Script
# Description: Performs comprehensive health checks on deployed services
# Usage: ./health-check.sh [environment] [service] [options]
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
NAMESPACE="${NAMESPACE:-default}"
TIMEOUT="${TIMEOUT:-300}"
CHECK_INTERVAL="${CHECK_INTERVAL:-10}"

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
Usage: $0 ENVIRONMENT [SERVICE] [OPTIONS]

Perform health checks on deployed services

ARGUMENTS:
    ENVIRONMENT                 Target environment (dev|staging|production)
    SERVICE                     Service to check (api|web|worker|all) [default: all]

OPTIONS:
    --timeout SECONDS           Timeout for health checks [default: 300]
    --interval SECONDS          Check interval [default: 10]
    --strict                    Fail on any warning
    --quick                     Quick health check (basic checks only)
    -h, --help                  Display this help message

EXAMPLES:
    $0 production api
    $0 staging all --timeout 600
    $0 dev web --quick
EOF
    exit 1
}

# Parse command line arguments
if [ $# -lt 1 ]; then
    log_error "Missing required arguments"
    usage
fi

ENVIRONMENT="$1"
SERVICE="${2:-all}"
shift
[ $# -gt 0 ] && shift

STRICT=false
QUICK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        --strict)
            STRICT=true
            shift
            ;;
        --quick)
            QUICK=true
            shift
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

# Set namespace based on environment
case "$ENVIRONMENT" in
    dev|development)
        NAMESPACE="development"
        ;;
    staging)
        NAMESPACE="staging"
        ;;
    prod|production)
        NAMESPACE="production"
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Health check results
declare -A HEALTH_STATUS
OVERALL_HEALTHY=true

# Check Kubernetes cluster connectivity
check_cluster_connectivity() {
    log_info "Checking Kubernetes cluster connectivity..."

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        return 1
    fi

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace not found: $NAMESPACE"
        return 1
    fi

    log_success "Cluster connectivity OK"
    return 0
}

# Check pod status
check_pod_status() {
    local service=$1

    log_info "Checking pod status for $service..."

    # Get pod information
    local pods=$(kubectl get pods \
        --namespace="$NAMESPACE" \
        -l "app=${service}" \
        -o json 2>/dev/null || echo '{"items":[]}')

    local total_pods=$(echo "$pods" | jq -r '.items | length')

    if [ "$total_pods" -eq 0 ]; then
        log_error "No pods found for $service"
        HEALTH_STATUS["${service}_pods"]="FAILED"
        return 1
    fi

    # Count ready pods
    local ready_pods=$(echo "$pods" | jq -r '.items[].status.conditions[] | select(.type=="Ready" and .status=="True")' | wc -l)

    # Count running pods
    local running_pods=$(echo "$pods" | jq -r '.items[].status.phase' | grep -c "Running" || echo 0)

    log_info "Total pods: $total_pods"
    log_info "Running pods: $running_pods"
    log_info "Ready pods: $ready_pods"

    # Check for issues
    if [ "$ready_pods" -eq "$total_pods" ]; then
        log_success "All pods are ready ($ready_pods/$total_pods)"
        HEALTH_STATUS["${service}_pods"]="HEALTHY"
    elif [ "$ready_pods" -gt 0 ]; then
        log_warning "Some pods are not ready ($ready_pods/$total_pods)"
        HEALTH_STATUS["${service}_pods"]="DEGRADED"
        [ "$STRICT" = true ] && return 1
    else
        log_error "No pods are ready"
        HEALTH_STATUS["${service}_pods"]="FAILED"
        return 1
    fi

    # Check for pod restarts
    local restarts=$(echo "$pods" | jq -r '.items[].status.containerStatuses[].restartCount' | awk '{sum+=$1} END {print sum}')
    log_info "Total restarts: ${restarts:-0}"

    if [ "${restarts:-0}" -gt 5 ]; then
        log_warning "High number of pod restarts detected"
        [ "$STRICT" = true ] && return 1
    fi

    return 0
}

# Check deployment status
check_deployment_status() {
    local service=$1

    log_info "Checking deployment status for $service..."

    if ! kubectl get deployment "$service" --namespace="$NAMESPACE" &> /dev/null; then
        log_error "Deployment not found: $service"
        HEALTH_STATUS["${service}_deployment"]="FAILED"
        return 1
    fi

    # Get deployment info
    local desired=$(kubectl get deployment "$service" --namespace="$NAMESPACE" -o jsonpath='{.spec.replicas}')
    local current=$(kubectl get deployment "$service" --namespace="$NAMESPACE" -o jsonpath='{.status.replicas}')
    local available=$(kubectl get deployment "$service" --namespace="$NAMESPACE" -o jsonpath='{.status.availableReplicas}')
    local ready=$(kubectl get deployment "$service" --namespace="$NAMESPACE" -o jsonpath='{.status.readyReplicas}')

    log_info "Desired replicas: ${desired:-0}"
    log_info "Current replicas: ${current:-0}"
    log_info "Available replicas: ${available:-0}"
    log_info "Ready replicas: ${ready:-0}"

    if [ "${available:-0}" -eq "${desired:-0}" ] && [ "${desired:-0}" -gt 0 ]; then
        log_success "Deployment is healthy"
        HEALTH_STATUS["${service}_deployment"]="HEALTHY"
        return 0
    elif [ "${available:-0}" -gt 0 ]; then
        log_warning "Deployment is partially available"
        HEALTH_STATUS["${service}_deployment"]="DEGRADED"
        [ "$STRICT" = true ] && return 1
        return 0
    else
        log_error "Deployment is not available"
        HEALTH_STATUS["${service}_deployment"]="FAILED"
        return 1
    fi
}

# Check service endpoints
check_service_endpoints() {
    local service=$1

    log_info "Checking service endpoints for $service..."

    if ! kubectl get service "$service" --namespace="$NAMESPACE" &> /dev/null; then
        log_warning "Service not found: $service"
        HEALTH_STATUS["${service}_service"]="WARNING"
        return 0
    fi

    # Get endpoints
    local endpoints=$(kubectl get endpoints "$service" --namespace="$NAMESPACE" -o json 2>/dev/null || echo '{}')
    local endpoint_count=$(echo "$endpoints" | jq -r '.subsets[].addresses | length' 2>/dev/null || echo 0)

    log_info "Endpoint count: $endpoint_count"

    if [ "$endpoint_count" -gt 0 ]; then
        log_success "Service has active endpoints"
        HEALTH_STATUS["${service}_service"]="HEALTHY"
        return 0
    else
        log_warning "Service has no active endpoints"
        HEALTH_STATUS["${service}_service"]="DEGRADED"
        [ "$STRICT" = true ] && return 1
        return 0
    fi
}

# Check HTTP endpoint health
check_http_health() {
    local service=$1

    if [ "$QUICK" = true ]; then
        log_info "Skipping HTTP health check (quick mode)"
        return 0
    fi

    log_info "Checking HTTP health for $service..."

    # Try to get service URL
    local service_url=""

    # Try LoadBalancer
    service_url=$(kubectl get service "${service}" \
        --namespace="$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")

    # Try Ingress if LoadBalancer not found
    if [ -z "$service_url" ]; then
        service_url=$(kubectl get ingress \
            --namespace="$NAMESPACE" \
            -l "app=${service}" \
            -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null || echo "")
    fi

    if [ -z "$service_url" ]; then
        log_info "No external URL found, using port-forward for health check"

        # Start port-forward
        kubectl port-forward \
            --namespace="$NAMESPACE" \
            "svc/${service}" 8080:80 &> /dev/null &
        local pf_pid=$!
        sleep 3

        service_url="localhost:8080"
    fi

    # Check health endpoint
    local max_attempts=$((TIMEOUT / CHECK_INTERVAL))
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://${service_url}/health" > /dev/null 2>&1; then
            log_success "HTTP health check passed for $service"
            HEALTH_STATUS["${service}_http"]="HEALTHY"
            [ -n "${pf_pid:-}" ] && kill "$pf_pid" 2>/dev/null || true
            return 0
        fi

        log_info "Attempt $attempt/$max_attempts: Waiting for service to respond..."
        sleep "$CHECK_INTERVAL"
        ((attempt++))
    done

    log_error "HTTP health check failed for $service"
    HEALTH_STATUS["${service}_http"]="FAILED"
    [ -n "${pf_pid:-}" ] && kill "$pf_pid" 2>/dev/null || true
    return 1
}

# Check resource usage
check_resource_usage() {
    local service=$1

    if [ "$QUICK" = true ]; then
        log_info "Skipping resource usage check (quick mode)"
        return 0
    fi

    log_info "Checking resource usage for $service..."

    # Get pod metrics
    if ! kubectl top pods \
        --namespace="$NAMESPACE" \
        -l "app=${service}" &> /dev/null; then
        log_warning "Metrics not available (metrics-server may not be installed)"
        return 0
    fi

    local metrics=$(kubectl top pods \
        --namespace="$NAMESPACE" \
        -l "app=${service}" \
        --no-headers 2>/dev/null || echo "")

    if [ -n "$metrics" ]; then
        log_info "Resource usage:"
        echo "$metrics" | while read -r line; do
            log_info "  $line"
        done
        HEALTH_STATUS["${service}_resources"]="HEALTHY"
    fi

    return 0
}

# Check recent logs for errors
check_logs_for_errors() {
    local service=$1

    if [ "$QUICK" = true ]; then
        log_info "Skipping log check (quick mode)"
        return 0
    fi

    log_info "Checking recent logs for errors in $service..."

    local error_count=$(kubectl logs \
        --namespace="$NAMESPACE" \
        -l "app=${service}" \
        --tail=100 \
        --since=5m 2>&1 | grep -ic "error" || echo 0)

    local critical_count=$(kubectl logs \
        --namespace="$NAMESPACE" \
        -l "app=${service}" \
        --tail=100 \
        --since=5m 2>&1 | grep -ic "critical\|fatal" || echo 0)

    log_info "Error count (last 5 min): $error_count"
    log_info "Critical count (last 5 min): $critical_count"

    if [ "$critical_count" -gt 0 ]; then
        log_error "Critical errors found in logs"
        HEALTH_STATUS["${service}_logs"]="FAILED"
        return 1
    elif [ "$error_count" -gt 10 ]; then
        log_warning "High number of errors in logs"
        HEALTH_STATUS["${service}_logs"]="DEGRADED"
        [ "$STRICT" = true ] && return 1
        return 0
    else
        log_success "No critical issues in logs"
        HEALTH_STATUS["${service}_logs"]="HEALTHY"
        return 0
    fi
}

# Perform health check for a single service
health_check_service() {
    local service=$1
    local service_healthy=true

    log_info "========================================="
    log_info "Health Check: $service"
    log_info "Environment: $ENVIRONMENT"
    log_info "Namespace: $NAMESPACE"
    log_info "========================================="
    echo ""

    # Run all checks
    check_pod_status "$service" || service_healthy=false
    echo ""

    check_deployment_status "$service" || service_healthy=false
    echo ""

    check_service_endpoints "$service" || service_healthy=false
    echo ""

    check_http_health "$service" || service_healthy=false
    echo ""

    check_resource_usage "$service" || service_healthy=false
    echo ""

    check_logs_for_errors "$service" || service_healthy=false
    echo ""

    if [ "$service_healthy" = true ]; then
        log_success "Overall health check PASSED for $service"
        return 0
    else
        log_error "Overall health check FAILED for $service"
        OVERALL_HEALTHY=false
        return 1
    fi
}

# Generate health report
generate_health_report() {
    log_info "========================================="
    log_info "Health Check Summary"
    log_info "========================================="

    for key in "${!HEALTH_STATUS[@]}"; do
        local status="${HEALTH_STATUS[$key]}"
        case "$status" in
            HEALTHY)
                log_success "$key: $status"
                ;;
            DEGRADED|WARNING)
                log_warning "$key: $status"
                ;;
            FAILED)
                log_error "$key: $status"
                ;;
        esac
    done

    echo ""

    if [ "$OVERALL_HEALTHY" = true ]; then
        log_success "Overall system health: HEALTHY"
        return 0
    else
        log_error "Overall system health: UNHEALTHY"
        return 1
    fi
}

# Main health check process
main() {
    log_info "Starting health check..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Service: $SERVICE"
    log_info "Namespace: $NAMESPACE"
    echo ""

    # Check cluster connectivity
    if ! check_cluster_connectivity; then
        exit 1
    fi
    echo ""

    # Perform health checks
    if [ "$SERVICE" = "all" ]; then
        SERVICES=("api" "web" "worker")

        for svc in "${SERVICES[@]}"; do
            health_check_service "$svc"
            echo ""
        done
    else
        health_check_service "$SERVICE"
        echo ""
    fi

    # Generate report
    generate_health_report

    if [ "$OVERALL_HEALTHY" = true ]; then
        exit 0
    else
        exit 1
    fi
}

# Cleanup function
cleanup() {
    log_warning "Health check interrupted"
    exit 130
}

# Trap SIGINT (Ctrl+C)
trap cleanup INT

# Run main function
main
