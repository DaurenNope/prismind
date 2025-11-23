#!/bin/bash
# Docker build script for Prismind services
# Builds all Docker images with optimizations and caching

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BUILD_CONTEXT="${BUILD_CONTEXT:-.}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
BUILD_PLATFORM="${BUILD_PLATFORM:-linux/amd64}"
CACHE_FROM="${CACHE_FROM:-}"

# Services to build
SERVICES=("api" "api-gateway" "worker-publisher" "worker-rewriter" "worker-collector-threads" "worker-collector-twitter")

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi

    log_info "Docker is available"
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    log_info "Docker Compose is available"
}

build_service() {
    local service=$1
    log_info "Building service: $service"

    # Determine Dockerfile path
    local dockerfile=""
    case $service in
        api)
            dockerfile="services/api/Dockerfile"
            ;;
        api-gateway)
            dockerfile="services/gateway/Dockerfile"
            ;;
        worker-*)
            dockerfile="services/worker/Dockerfile"
            ;;
        *)
            log_error "Unknown service: $service"
            return 1
            ;;
    esac

    # Build with cache
    local build_args=(
        "--file" "$dockerfile"
        "--build-arg" "BUILDKIT_INLINE_CACHE=1"
    )

    if [ -n "$CACHE_FROM" ]; then
        build_args+=("--cache-from" "$CACHE_FROM")
    fi

    build_args+=(
        "--tag" "prismind-$service:latest"
        "$BUILD_CONTEXT"
    )

    if ! docker build "${build_args[@]}"; then
        log_error "Failed to build $service"
        return 1
    fi

    log_info "Successfully built $service"
}

build_all_services() {
    log_info "Building all services..."

    # Build base services first
    for service in "${SERVICES[@]}"; do
        build_service "$service" || {
            log_error "Failed to build $service. Aborting."
            exit 1
        }
    done

    log_info "All services built successfully"
}

build_with_compose() {
    log_info "Building with docker-compose..."

    if docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" build --parallel
    else
        docker-compose -f "$COMPOSE_FILE" build --parallel
    fi

    if [ $? -eq 0 ]; then
        log_info "All services built successfully with docker-compose"
    else
        log_error "Failed to build services with docker-compose"
        exit 1
    fi
}

verify_images() {
    log_info "Verifying Docker images..."

    for service in "${SERVICES[@]}"; do
        local image_name="prismind-${service//-/_}"
        if docker images | grep -q "prismind-$service"; then
            log_info "Image verified: prismind-$service"
        else
            log_warn "Image not found: prismind-$service"
        fi
    done
}

cleanup_old_images() {
    if [ "${CLEANUP_OLD:-false}" = "true" ]; then
        log_info "Cleaning up old images..."
        docker image prune -f
        log_info "Cleanup completed"
    fi
}

main() {
    log_info "Starting Docker build process..."
    log_info "Build context: $BUILD_CONTEXT"
    log_info "Platform: $BUILD_PLATFORM"

    check_docker
    check_docker_compose

    # Choose build method
    if [ "${USE_COMPOSE:-false}" = "true" ]; then
        build_with_compose
    else
        build_all_services
    fi

    verify_images
    cleanup_old_images

    log_info "Build process completed successfully!"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --compose)
            USE_COMPOSE=true
            shift
            ;;
        --cleanup)
            CLEANUP_OLD=true
            shift
            ;;
        --platform)
            BUILD_PLATFORM="$2"
            shift 2
            ;;
        --cache-from)
            CACHE_FROM="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --compose       Use docker-compose to build"
            echo "  --cleanup       Clean up old images after build"
            echo "  --platform      Set build platform (default: linux/amd64)"
            echo "  --cache-from    Use image as cache source"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

main






