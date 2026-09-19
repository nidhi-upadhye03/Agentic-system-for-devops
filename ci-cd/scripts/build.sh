#!/bin/bash

################################################################################
# Docker Image Build Script
# Description: Builds and tags Docker images for all services
# Usage: ./build.sh [service] [environment] [version]
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
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF="${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')}"

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

Build Docker images for services

OPTIONS:
    -s, --service SERVICE       Service to build (api|web|worker|all) [default: all]
    -e, --environment ENV       Environment (dev|staging|prod) [default: dev]
    -v, --version VERSION       Version tag [default: latest]
    -p, --push                  Push images to registry
    -c, --cache                 Use cache when building
    --platform PLATFORM         Target platform (linux/amd64,linux/arm64)
    -h, --help                  Display this help message

EXAMPLES:
    $0 --service api --version v1.2.3 --push
    $0 --service all --environment prod --push
    $0 -s web -e staging -v v1.0.0-rc1
EOF
    exit 1
}

# Parse command line arguments
SERVICE="all"
ENVIRONMENT="dev"
VERSION="latest"
PUSH=false
USE_CACHE="--no-cache"
PLATFORM="linux/amd64"

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -c|--cache)
            USE_CACHE=""
            shift
            ;;
        --platform)
            PLATFORM="$2"
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

# Validate service
validate_service() {
    local service=$1
    if [[ ! "$service" =~ ^(api|web|worker|all)$ ]]; then
        log_error "Invalid service: $service"
        log_info "Valid services: api, web, worker, all"
        exit 1
    fi
}

# Build a single service
build_service() {
    local service=$1
    local image_tag="${REGISTRY}/${IMAGE_NAME}-${service}:${VERSION}"
    local dockerfile="./docker/Dockerfile.${service}"

    log_info "Building $service service..."
    log_info "Image: $image_tag"
    log_info "Dockerfile: $dockerfile"

    if [ ! -f "$dockerfile" ]; then
        log_error "Dockerfile not found: $dockerfile"
        return 1
    fi

    # Build arguments
    BUILD_ARGS=(
        --build-arg "BUILD_DATE=${BUILD_DATE}"
        --build-arg "VCS_REF=${VCS_REF}"
        --build-arg "VERSION=${VERSION}"
        --build-arg "ENVIRONMENT=${ENVIRONMENT}"
        --platform "${PLATFORM}"
    )

    # Additional tags
    TAGS=(
        -t "${image_tag}"
        -t "${REGISTRY}/${IMAGE_NAME}-${service}:${ENVIRONMENT}"
    )

    if [ "$ENVIRONMENT" == "prod" ]; then
        TAGS+=(-t "${REGISTRY}/${IMAGE_NAME}-${service}:latest")
    fi

    # Build the image
    if docker build \
        $USE_CACHE \
        "${BUILD_ARGS[@]}" \
        "${TAGS[@]}" \
        -f "$dockerfile" \
        . ; then
        log_success "Built $service image successfully"
    else
        log_error "Failed to build $service image"
        return 1
    fi

    # Tag with commit SHA
    if [ "$VCS_REF" != "unknown" ]; then
        docker tag "$image_tag" "${REGISTRY}/${IMAGE_NAME}-${service}:${VCS_REF}"
        log_info "Tagged with commit SHA: ${VCS_REF}"
    fi

    # Push to registry if requested
    if [ "$PUSH" = true ]; then
        log_info "Pushing $service image to registry..."
        for tag in "${TAGS[@]:1}"; do  # Skip the -t flag
            if docker push "$tag"; then
                log_success "Pushed: $tag"
            else
                log_error "Failed to push: $tag"
                return 1
            fi
        done

        if [ "$VCS_REF" != "unknown" ]; then
            docker push "${REGISTRY}/${IMAGE_NAME}-${service}:${VCS_REF}"
            log_success "Pushed commit SHA tag"
        fi
    fi

    # Get image size
    IMAGE_SIZE=$(docker images "$image_tag" --format "{{.Size}}")
    log_info "Image size: $IMAGE_SIZE"

    return 0
}

# Main build process
main() {
    log_info "Starting Docker build process..."
    log_info "Service: $SERVICE"
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    log_info "Registry: $REGISTRY"
    log_info "Platform: $PLATFORM"
    echo ""

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Check Docker daemon
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Login to registry if pushing
    if [ "$PUSH" = true ]; then
        log_info "Logging in to container registry..."
        if [ -n "${GITHUB_TOKEN:-}" ]; then
            echo "$GITHUB_TOKEN" | docker login "$REGISTRY" -u "$GITHUB_ACTOR" --password-stdin
        elif [ -n "${DOCKER_PASSWORD:-}" ]; then
            echo "$DOCKER_PASSWORD" | docker login "$REGISTRY" -u "${DOCKER_USERNAME}" --password-stdin
        else
            log_warning "No credentials found, assuming already logged in"
        fi
    fi

    # Build services
    if [ "$SERVICE" == "all" ]; then
        SERVICES=("api" "web" "worker")
        FAILED_SERVICES=()

        for svc in "${SERVICES[@]}"; do
            if ! build_service "$svc"; then
                FAILED_SERVICES+=("$svc")
            fi
            echo ""
        done

        if [ ${#FAILED_SERVICES[@]} -eq 0 ]; then
            log_success "All services built successfully!"
            exit 0
        else
            log_error "Failed to build services: ${FAILED_SERVICES[*]}"
            exit 1
        fi
    else
        validate_service "$SERVICE"
        if build_service "$SERVICE"; then
            log_success "Build completed successfully!"
            exit 0
        else
            log_error "Build failed!"
            exit 1
        fi
    fi
}

# Cleanup function
cleanup() {
    log_warning "Build interrupted"
    exit 130
}

# Trap SIGINT (Ctrl+C)
trap cleanup INT

# Run main function
main
