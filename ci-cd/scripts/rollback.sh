#!/bin/bash

################################################################################
# Rollback Script
# Description: Rollback deployments to previous versions
# Usage: ./rollback.sh [environment] [service] [options]
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
KUBECTL_TIMEOUT="${KUBECTL_TIMEOUT:-5m}"

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

Rollback deployments to previous versions

ARGUMENTS:
    ENVIRONMENT                 Target environment (dev|staging|production)
    SERVICE                     Service to rollback (api|web|worker|all) [default: all]

OPTIONS:
    --revision REVISION         Rollback to specific revision number
    --helm                      Use Helm for rollback (default)
    --kubectl                   Use kubectl for rollback
    --dry-run                   Show what would be rolled back
    --no-wait                   Don't wait for rollout to complete
    -h, --help                  Display this help message

EXAMPLES:
    $0 production api
    $0 staging all --revision 3
    $0 dev web --dry-run
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

REVISION=""
ROLLBACK_METHOD="helm"
DRY_RUN=false
WAIT=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --revision)
            REVISION="$2"
            shift 2
            ;;
        --helm)
            ROLLBACK_METHOD="helm"
            shift
            ;;
        --kubectl)
            ROLLBACK_METHOD="kubectl"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-wait)
            WAIT=false
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
        CLUSTER_NAME="${DEV_CLUSTER_NAME:-dev-cluster}"
        ;;
    staging)
        NAMESPACE="staging"
        CLUSTER_NAME="${STAGING_CLUSTER_NAME:-staging-cluster}"
        ;;
    prod|production)
        NAMESPACE="production"
        CLUSTER_NAME="${PROD_CLUSTER_NAME:-prod-cluster}"
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Check helm if using helm rollback
    if [ "$ROLLBACK_METHOD" = "helm" ]; then
        if ! command -v helm &> /dev/null; then
            log_error "helm is not installed"
            exit 1
        fi
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Get deployment history
get_deployment_history() {
    local service=$1

    log_info "Deployment history for $service:"

    if [ "$ROLLBACK_METHOD" = "helm" ]; then
        helm history "$service" --namespace="$NAMESPACE" --max=10 || true
    else
        kubectl rollout history "deployment/${service}" --namespace="$NAMESPACE" || true
    fi
}

# Get current version
get_current_version() {
    local service=$1

    log_info "Getting current version for $service..."

    if [ "$ROLLBACK_METHOD" = "helm" ]; then
        local current_version=$(helm list --namespace="$NAMESPACE" --filter="^${service}$" -o json | \
            jq -r '.[0].app_version' 2>/dev/null || echo "unknown")
        local chart_version=$(helm list --namespace="$NAMESPACE" --filter="^${service}$" -o json | \
            jq -r '.[0].chart' 2>/dev/null || echo "unknown")

        log_info "Current app version: $current_version"
        log_info "Current chart version: $chart_version"
    else
        local current_image=$(kubectl get deployment "$service" \
            --namespace="$NAMESPACE" \
            -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "unknown")

        log_info "Current image: $current_image"
    fi
}

# Create backup before rollback
create_backup() {
    local service=$1

    log_info "Creating backup before rollback..."

    local backup_dir="./backups/${ENVIRONMENT}/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup deployment
    kubectl get deployment "$service" \
        --namespace="$NAMESPACE" \
        -o yaml > "${backup_dir}/${service}-deployment.yaml" 2>/dev/null || true

    # Backup service
    kubectl get service "$service" \
        --namespace="$NAMESPACE" \
        -o yaml > "${backup_dir}/${service}-service.yaml" 2>/dev/null || true

    # Backup configmaps
    kubectl get configmaps \
        --namespace="$NAMESPACE" \
        -l "app=${service}" \
        -o yaml > "${backup_dir}/${service}-configmaps.yaml" 2>/dev/null || true

    log_success "Backup created at: $backup_dir"
}

# Rollback with Helm
rollback_with_helm() {
    local service=$1

    log_warning "Rolling back $service with Helm..."

    local helm_cmd="helm rollback ${service}"
    helm_cmd+=" --namespace=${NAMESPACE}"

    if [ -n "$REVISION" ]; then
        helm_cmd+=" ${REVISION}"
    fi

    if [ "$WAIT" = true ]; then
        helm_cmd+=" --wait --timeout=${KUBECTL_TIMEOUT}"
    fi

    if [ "$DRY_RUN" = true ]; then
        helm_cmd+=" --dry-run"
        log_info "[DRY RUN] Helm rollback command: $helm_cmd"
    fi

    if eval "$helm_cmd"; then
        log_success "Helm rollback successful for $service"
        return 0
    else
        log_error "Helm rollback failed for $service"
        return 1
    fi
}

# Rollback with kubectl
rollback_with_kubectl() {
    local service=$1

    log_warning "Rolling back $service with kubectl..."

    local kubectl_cmd="kubectl rollout undo deployment/${service}"
    kubectl_cmd+=" --namespace=${NAMESPACE}"

    if [ -n "$REVISION" ]; then
        kubectl_cmd+=" --to-revision=${REVISION}"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] kubectl rollback command: $kubectl_cmd"
        return 0
    fi

    if eval "$kubectl_cmd"; then
        log_success "kubectl rollback initiated for $service"

        # Wait for rollout if requested
        if [ "$WAIT" = true ]; then
            if kubectl rollout status "deployment/${service}" \
                --namespace="$NAMESPACE" \
                --timeout="${KUBECTL_TIMEOUT}"; then
                log_success "Rollback rollout completed for $service"
                return 0
            else
                log_error "Rollback rollout failed for $service"
                return 1
            fi
        fi
        return 0
    else
        log_error "kubectl rollback failed for $service"
        return 1
    fi
}

# Verify rollback success
verify_rollback() {
    local service=$1

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would verify rollback for $service"
        return 0
    fi

    log_info "Verifying rollback for $service..."

    # Check pod status
    local ready_pods=$(kubectl get pods \
        --namespace="$NAMESPACE" \
        -l "app=${service}" \
        -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o "True" | wc -l)

    local total_pods=$(kubectl get pods \
        --namespace="$NAMESPACE" \
        -l "app=${service}" \
        --no-headers | wc -l)

    log_info "Pods ready: $ready_pods/$total_pods"

    if [ "$ready_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
        log_success "All pods are ready after rollback"
    else
        log_warning "Some pods are not ready: $ready_pods/$total_pods"
    fi

    # Check for recent errors
    log_info "Checking for recent errors..."
    kubectl logs \
        --namespace="$NAMESPACE" \
        -l "app=${service}" \
        --tail=50 \
        --since=1m 2>&1 | grep -i "error" || log_info "No recent errors found"

    return 0
}

# Run health checks after rollback
run_health_checks() {
    local service=$1

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would run health checks for $service"
        return 0
    fi

    log_info "Running health checks after rollback..."

    # Wait a bit for the service to stabilize
    sleep 10

    # Check service endpoint
    local service_url=$(kubectl get service "${service}" \
        --namespace="$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")

    if [ -n "$service_url" ]; then
        if curl -sf "http://${service_url}/health" > /dev/null 2>&1; then
            log_success "Health check passed for $service"
            return 0
        else
            log_warning "Health check failed for $service"
            return 1
        fi
    else
        log_info "No external service URL found, skipping HTTP health check"
        return 0
    fi
}

# Send notification
send_notification() {
    local service=$1
    local status=$2

    log_info "Sending rollback notification..."

    # This would integrate with your notification system
    # Example: Slack, email, PagerDuty, etc.

    if [ "$status" = "success" ]; then
        log_info "Rollback notification: $service rolled back successfully in $ENVIRONMENT"
    else
        log_warning "Rollback notification: $service rollback failed in $ENVIRONMENT"
    fi
}

# Rollback a single service
rollback_service() {
    local service=$1

    log_warning "========================================="
    log_warning "ROLLING BACK: $service"
    log_warning "Environment: $ENVIRONMENT"
    log_warning "Namespace: $NAMESPACE"
    log_warning "Method: $ROLLBACK_METHOD"
    if [ -n "$REVISION" ]; then
        log_warning "Target Revision: $REVISION"
    fi
    log_warning "========================================="

    # Show deployment history
    get_deployment_history "$service"
    echo ""

    # Get current version
    get_current_version "$service"
    echo ""

    # Create backup
    if [ "$DRY_RUN" = false ]; then
        create_backup "$service"
        echo ""
    fi

    # Perform rollback
    if [ "$ROLLBACK_METHOD" = "helm" ]; then
        if ! rollback_with_helm "$service"; then
            send_notification "$service" "failed"
            return 1
        fi
    else
        if ! rollback_with_kubectl "$service"; then
            send_notification "$service" "failed"
            return 1
        fi
    fi

    echo ""

    # Verify rollback
    verify_rollback "$service"
    echo ""

    # Health checks
    run_health_checks "$service"
    echo ""

    send_notification "$service" "success"
    log_success "Rollback completed successfully for $service"
    return 0
}

# Main rollback process
main() {
    log_warning "========================================="
    log_warning "ROLLBACK INITIATED"
    log_warning "Environment: $ENVIRONMENT"
    log_warning "Service: $SERVICE"
    log_warning "========================================="
    echo ""

    # Confirmation for production
    if [ "$ENVIRONMENT" = "production" ] && [ "$DRY_RUN" = false ]; then
        log_warning "WARNING: You are about to rollback in PRODUCTION!"
        read -p "Type 'rollback' to confirm: " confirmation
        if [ "$confirmation" != "rollback" ]; then
            log_info "Rollback cancelled"
            exit 0
        fi
    fi

    check_prerequisites
    echo ""

    local failed_services=()

    if [ "$SERVICE" = "all" ]; then
        SERVICES=("api" "web" "worker")

        for svc in "${SERVICES[@]}"; do
            if ! rollback_service "$svc"; then
                failed_services+=("$svc")
            fi
            echo ""
        done

        if [ ${#failed_services[@]} -eq 0 ]; then
            log_success "All services rolled back successfully!"
            exit 0
        else
            log_error "Failed to rollback services: ${failed_services[*]}"
            exit 1
        fi
    else
        if rollback_service "$SERVICE"; then
            log_success "Rollback completed successfully!"
            exit 0
        else
            log_error "Rollback failed!"
            exit 1
        fi
    fi
}

# Cleanup function
cleanup() {
    log_warning "Rollback interrupted"
    exit 130
}

# Trap SIGINT (Ctrl+C)
trap cleanup INT

# Run main function
main
