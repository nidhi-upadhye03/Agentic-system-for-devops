#!/bin/bash

################################################################################
# Deployment Orchestration Script
# Description: Deploys services to Kubernetes clusters
# Usage: ./deploy.sh [service] [environment] [version]
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
REGISTRY="${REGISTRY:-ghcr.io}"
IMAGE_NAME="${IMAGE_NAME:-myorg/myapp}"
NAMESPACE="${NAMESPACE:-default}"
HELM_TIMEOUT="${HELM_TIMEOUT:-10m}"
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
Usage: $0 SERVICE ENVIRONMENT VERSION [OPTIONS]

Deploy services to Kubernetes cluster

ARGUMENTS:
    SERVICE                     Service to deploy (api|web|worker|all)
    ENVIRONMENT                 Target environment (dev|staging|production)
    VERSION                     Version/tag to deploy

OPTIONS:
    --dry-run                   Perform a dry run without actual deployment
    --helm                      Use Helm for deployment (default)
    --kubectl                   Use kubectl for deployment
    --rollback                  Rollback to previous version
    --force                     Force deployment even if checks fail
    --skip-health               Skip health checks
    -h, --help                  Display this help message

EXAMPLES:
    $0 api dev v1.2.3
    $0 web production v2.0.0 --dry-run
    $0 all staging v1.5.0-rc1
EOF
    exit 1
}

# Parse command line arguments
if [ $# -lt 3 ]; then
    log_error "Missing required arguments"
    usage
fi

SERVICE="$1"
ENVIRONMENT="$2"
VERSION="$3"
shift 3

DRY_RUN=false
DEPLOYMENT_METHOD="helm"
ROLLBACK=false
FORCE=false
SKIP_HEALTH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --helm)
            DEPLOYMENT_METHOD="helm"
            shift
            ;;
        --kubectl)
            DEPLOYMENT_METHOD="kubectl"
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --skip-health)
            SKIP_HEALTH=true
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

# Validate service
validate_service() {
    local service=$1
    if [[ ! "$service" =~ ^(api|web|worker|all)$ ]]; then
        log_error "Invalid service: $service"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Check helm if using helm deployment
    if [ "$DEPLOYMENT_METHOD" = "helm" ]; then
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

# Verify image exists
verify_image() {
    local service=$1
    local image="${REGISTRY}/${IMAGE_NAME}-${service}:${VERSION}"

    log_info "Verifying image exists: $image"

    if docker manifest inspect "$image" &> /dev/null; then
        log_success "Image verified: $image"
        return 0
    else
        log_error "Image not found: $image"
        return 1
    fi
}

# Create namespace if not exists
ensure_namespace() {
    log_info "Ensuring namespace exists: $NAMESPACE"

    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace already exists"
    else
        if [ "$DRY_RUN" = false ]; then
            kubectl create namespace "$NAMESPACE"
            log_success "Created namespace: $NAMESPACE"
        else
            log_info "[DRY RUN] Would create namespace: $NAMESPACE"
        fi
    fi
}

# Deploy with Helm
deploy_with_helm() {
    local service=$1
    local chart_path="./helm/${service}"

    log_info "Deploying $service with Helm..."

    if [ ! -d "$chart_path" ]; then
        log_error "Helm chart not found: $chart_path"
        return 1
    fi

    local helm_cmd="helm upgrade --install ${service}"
    helm_cmd+=" ${chart_path}"
    helm_cmd+=" --namespace ${NAMESPACE}"
    helm_cmd+=" --set image.repository=${REGISTRY}/${IMAGE_NAME}-${service}"
    helm_cmd+=" --set image.tag=${VERSION}"
    helm_cmd+=" --set environment=${ENVIRONMENT}"

    # Environment-specific configurations
    case "$ENVIRONMENT" in
        production)
            helm_cmd+=" --set replicaCount=5"
            helm_cmd+=" --set autoscaling.minReplicas=5"
            helm_cmd+=" --set autoscaling.maxReplicas=20"
            helm_cmd+=" --set resources.requests.cpu=1000m"
            helm_cmd+=" --set resources.requests.memory=1Gi"
            ;;
        staging)
            helm_cmd+=" --set replicaCount=3"
            helm_cmd+=" --set autoscaling.minReplicas=3"
            helm_cmd+=" --set autoscaling.maxReplicas=10"
            helm_cmd+=" --set resources.requests.cpu=500m"
            helm_cmd+=" --set resources.requests.memory=512Mi"
            ;;
        development)
            helm_cmd+=" --set replicaCount=2"
            helm_cmd+=" --set autoscaling.enabled=false"
            helm_cmd+=" --set resources.requests.cpu=250m"
            helm_cmd+=" --set resources.requests.memory=256Mi"
            ;;
    esac

    helm_cmd+=" --wait --timeout=${HELM_TIMEOUT}"

    if [ "$DRY_RUN" = true ]; then
        helm_cmd+=" --dry-run --debug"
        log_info "[DRY RUN] Helm command: $helm_cmd"
    fi

    if eval "$helm_cmd"; then
        log_success "Helm deployment successful for $service"
        return 0
    else
        log_error "Helm deployment failed for $service"
        return 1
    fi
}

# Deploy with kubectl
deploy_with_kubectl() {
    local service=$1
    local manifest_path="./k8s/${ENVIRONMENT}/${service}"

    log_info "Deploying $service with kubectl..."

    if [ ! -d "$manifest_path" ]; then
        log_error "Kubernetes manifests not found: $manifest_path"
        return 1
    fi

    # Update image in manifests
    find "$manifest_path" -name "*.yaml" -o -name "*.yml" | while read -r file; do
        log_info "Applying manifest: $file"
        if [ "$DRY_RUN" = true ]; then
            kubectl apply -f "$file" --namespace="$NAMESPACE" --dry-run=client
        else
            kubectl apply -f "$file" --namespace="$NAMESPACE"
        fi
    done

    # Update deployment image
    local deployment_name="${service}"
    local image="${REGISTRY}/${IMAGE_NAME}-${service}:${VERSION}"

    if [ "$DRY_RUN" = false ]; then
        kubectl set image "deployment/${deployment_name}" \
            "${service}=${image}" \
            --namespace="$NAMESPACE" \
            --record

        log_success "kubectl deployment successful for $service"
    else
        log_info "[DRY RUN] Would set image: $image"
    fi

    return 0
}

# Wait for rollout to complete
wait_for_rollout() {
    local service=$1

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would wait for rollout: $service"
        return 0
    fi

    log_info "Waiting for rollout to complete: $service"

    if kubectl rollout status "deployment/${service}" \
        --namespace="$NAMESPACE" \
        --timeout="${KUBECTL_TIMEOUT}"; then
        log_success "Rollout completed successfully for $service"
        return 0
    else
        log_error "Rollout failed for $service"
        return 1
    fi
}

# Run health checks
run_health_checks() {
    local service=$1

    if [ "$SKIP_HEALTH" = true ]; then
        log_info "Skipping health checks (--skip-health flag)"
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would run health checks for $service"
        return 0
    fi

    log_info "Running health checks for $service..."

    # Get service endpoint
    local service_url=$(kubectl get service "${service}" \
        --namespace="$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")

    if [ -z "$service_url" ]; then
        log_warning "Could not determine service URL, checking pod health instead"

        # Check pod status
        local ready_pods=$(kubectl get pods \
            --namespace="$NAMESPACE" \
            -l "app=${service}" \
            -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o "True" | wc -l)

        if [ "$ready_pods" -gt 0 ]; then
            log_success "Health check passed: $ready_pods pods ready"
            return 0
        else
            log_error "Health check failed: No ready pods found"
            return 1
        fi
    fi

    # Check HTTP endpoint
    for i in {1..30}; do
        if curl -sf "http://${service_url}/health" > /dev/null 2>&1; then
            log_success "Health check passed for $service"
            return 0
        fi
        log_info "Waiting for service to be healthy... ($i/30)"
        sleep 10
    done

    log_error "Health check failed for $service"
    return 1
}

# Rollback deployment
rollback_deployment() {
    local service=$1

    log_warning "Rolling back deployment for $service..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would rollback: $service"
        return 0
    fi

    if [ "$DEPLOYMENT_METHOD" = "helm" ]; then
        if helm rollback "$service" --namespace="$NAMESPACE" --wait; then
            log_success "Rollback successful for $service"
            return 0
        else
            log_error "Rollback failed for $service"
            return 1
        fi
    else
        if kubectl rollout undo "deployment/${service}" --namespace="$NAMESPACE"; then
            log_success "Rollback successful for $service"
            return 0
        else
            log_error "Rollback failed for $service"
            return 1
        fi
    fi
}

# Deploy a single service
deploy_service() {
    local service=$1

    log_info "========================================="
    log_info "Deploying $service"
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    log_info "Namespace: $NAMESPACE"
    log_info "Method: $DEPLOYMENT_METHOD"
    log_info "========================================="

    # Verify image
    if [ "$FORCE" = false ] && [ "$DRY_RUN" = false ]; then
        if ! verify_image "$service"; then
            log_error "Image verification failed"
            return 1
        fi
    fi

    # Deploy based on method
    if [ "$DEPLOYMENT_METHOD" = "helm" ]; then
        if ! deploy_with_helm "$service"; then
            if [ "$ROLLBACK" = true ]; then
                rollback_deployment "$service"
            fi
            return 1
        fi
    else
        if ! deploy_with_kubectl "$service"; then
            if [ "$ROLLBACK" = true ]; then
                rollback_deployment "$service"
            fi
            return 1
        fi
    fi

    # Wait for rollout
    if ! wait_for_rollout "$service"; then
        if [ "$ROLLBACK" = true ]; then
            rollback_deployment "$service"
        fi
        return 1
    fi

    # Health checks
    if ! run_health_checks "$service"; then
        if [ "$ROLLBACK" = true ]; then
            rollback_deployment "$service"
        fi
        return 1
    fi

    log_success "Deployment successful for $service"
    return 0
}

# Main deployment process
main() {
    log_info "Starting deployment process..."
    echo ""

    validate_service "$SERVICE"
    check_prerequisites
    ensure_namespace

    echo ""

    local failed_services=()

    if [ "$SERVICE" = "all" ]; then
        SERVICES=("api" "web" "worker")

        for svc in "${SERVICES[@]}"; do
            if ! deploy_service "$svc"; then
                failed_services+=("$svc")
            fi
            echo ""
        done

        if [ ${#failed_services[@]} -eq 0 ]; then
            log_success "All services deployed successfully!"
            exit 0
        else
            log_error "Failed to deploy services: ${failed_services[*]}"
            exit 1
        fi
    else
        if deploy_service "$SERVICE"; then
            log_success "Deployment completed successfully!"
            exit 0
        else
            log_error "Deployment failed!"
            exit 1
        fi
    fi
}

# Cleanup function
cleanup() {
    log_warning "Deployment interrupted"
    exit 130
}

# Trap SIGINT (Ctrl+C)
trap cleanup INT

# Run main function
main
