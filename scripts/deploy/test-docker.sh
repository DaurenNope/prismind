#!/bin/bash
# Docker test script for Prismind services
# Tests Docker containers, health checks, and basic functionality

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
TIMEOUT="${TIMEOUT:-120}"
HEALTH_CHECK_INTERVAL=5
MAX_HEALTH_CHECK_ATTEMPTS=24

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running."
        exit 1
    fi

    log_info "Docker is available"
}

wait_for_service() {
    local service=$1
    local health_endpoint=$2
    local attempts=0

    log_test "Waiting for $service to be healthy..."

    while [ $attempts -lt $MAX_HEALTH_CHECK_ATTEMPTS ]; do
        if docker compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy\|running"; then
            # Check if it's actually responding
            if curl -sf "$health_endpoint" > /dev/null 2>&1; then
                log_info "$service is healthy"
                return 0
            fi
        fi

        attempts=$((attempts + 1))
        sleep $HEALTH_CHECK_INTERVAL
    done

    log_error "$service did not become healthy within timeout"
    return 1
}

test_redis() {
    log_test "Testing Redis service..."

    if docker compose -f "$COMPOSE_FILE" ps redis | grep -q "healthy"; then
        log_info "Redis container is healthy"
        
        # Test Redis connection
        if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping | grep -q "PONG"; then
            log_info "Redis connection test: PASSED"
            return 0
        else
            log_error "Redis connection test: FAILED"
            return 1
        fi
    else
        log_error "Redis container is not healthy"
        return 1
    fi
}

test_api() {
    log_test "Testing API service..."

    # Wait for API to be ready
    if wait_for_service "api" "http://localhost:8000/health/live"; then
        log_info "API is accessible"

        # Test health endpoint
        if curl -sf http://localhost:8000/health > /dev/null; then
            log_info "API health endpoint: PASSED"
        else
            log_error "API health endpoint: FAILED"
            return 1
        fi

        # Test readiness endpoint
        if curl -sf http://localhost:8000/health/ready > /dev/null; then
            log_info "API readiness endpoint: PASSED"
        else
            log_warn "API readiness endpoint: FAILED (may not be implemented)"
        fi

        return 0
    else
        log_error "API service test: FAILED"
        return 1
    fi
}

test_api_gateway() {
    log_test "Testing API Gateway service..."

    # Wait for gateway to be ready
    if wait_for_service "api-gateway" "http://localhost:8080/health"; then
        log_info "API Gateway is accessible"

        # Test health endpoint
        if curl -sf http://localhost:8080/health > /dev/null; then
            log_info "API Gateway health endpoint: PASSED"
            return 0
        else
            log_error "API Gateway health endpoint: FAILED"
            return 1
        fi
    else
        log_error "API Gateway service test: FAILED"
        return 1
    fi
}

test_workers() {
    log_test "Testing Worker services..."

    local workers=("worker-publisher" "worker-rewriter" "worker-collector-threads" "worker-collector-twitter")
    local all_passed=true

    for worker in "${workers[@]}"; do
        if docker compose -f "$COMPOSE_FILE" ps "$worker" | grep -q "running"; then
            log_info "$worker is running"
        else
            log_error "$worker is not running"
            all_passed=false
        fi
    done

    if [ "$all_passed" = true ]; then
        log_info "All worker services are running"
        return 0
    else
        log_error "Some worker services failed"
        return 1
    fi
}

test_ollama() {
    log_test "Testing Ollama service..."

    if docker compose -f "$COMPOSE_FILE" ps ollama | grep -q "healthy"; then
        log_info "Ollama container is healthy"
        
        # Test Ollama API
        if curl -sf http://localhost:11434/api/tags > /dev/null; then
            log_info "Ollama API test: PASSED"
            return 0
        else
            log_error "Ollama API test: FAILED"
            return 1
        fi
    else
        log_warn "Ollama container is not healthy (may be optional)"
        return 0
    fi
}

check_container_logs() {
    log_test "Checking container logs for errors..."

    local services=("api" "api-gateway" "redis" "worker-publisher")
    local errors_found=false

    for service in "${services[@]}"; do
        log_info "Checking logs for $service..."
        
        if docker compose -f "$COMPOSE_FILE" logs --tail=50 "$service" 2>&1 | grep -i "error\|exception\|fatal" > /dev/null; then
            log_warn "Errors found in $service logs"
            errors_found=true
        fi
    done

    if [ "$errors_found" = true ]; then
        log_warn "Some errors were found in logs (review manually)"
        return 0
    else
        log_info "No critical errors found in logs"
        return 0
    fi
}

test_networking() {
    log_test "Testing service networking..."

    # Test API can reach Redis
    if docker compose -f "$COMPOSE_FILE" exec -T api python -c "
import redis
import os
try:
    r = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))
    r.ping()
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
    exit(1)
" 2>&1 | grep -q "SUCCESS"; then
        log_info "API -> Redis connectivity: PASSED"
    else
        log_error "API -> Redis connectivity: FAILED"
        return 1
    fi

    return 0
}

print_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Docker Test Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo "Container Status:"
    docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
}

main() {
    log_info "Starting Docker test suite..."
    log_info "Compose file: $COMPOSE_FILE"
    log_info "Timeout: ${TIMEOUT}s"

    check_docker

    # Start services if not running
    if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_info "Starting services..."
        docker compose -f "$COMPOSE_FILE" up -d
        sleep 10
    fi

    local test_results=0

    # Run tests
    test_redis || test_results=$((test_results + 1))
    test_ollama || test_results=$((test_results + 0))  # Optional
    test_api || test_results=$((test_results + 1))
    test_api_gateway || test_results=$((test_results + 1))
    test_workers || test_results=$((test_results + 1))
    test_networking || test_results=$((test_results + 1))
    check_container_logs || test_results=$((test_results + 0))  # Non-critical

    print_summary

    if [ $test_results -eq 0 ]; then
        log_info "All tests passed!"
        exit 0
    else
        log_error "$test_results test(s) failed"
        exit 1
    fi
}

# Parse arguments
if [ "${1:-}" = "--stop" ]; then
    log_info "Stopping services..."
    docker compose -f "$COMPOSE_FILE" down
    exit 0
elif [ "${1:-}" = "--logs" ]; then
    docker compose -f "$COMPOSE_FILE" logs -f
    exit 0
elif [ "${1:-}" = "--help" ]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --stop       Stop all services after testing"
    echo "  --logs       Show logs from all services"
    echo "  --help       Show this help message"
    exit 0
fi

main






