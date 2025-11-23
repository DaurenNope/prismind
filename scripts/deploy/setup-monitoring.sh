#!/bin/bash
# Monitoring setup script for Prismind
# Configures error tracking, metrics, and monitoring dashboards

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_env_file() {
    if [ ! -f ".env" ]; then
        log_warn ".env file not found. Creating from example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "Created .env file. Please update with your configuration."
        else
            log_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    fi
}

setup_sentry() {
    log_step "Setting up Sentry error tracking..."

    if [ -z "${SENTRY_DSN:-}" ]; then
        log_warn "SENTRY_DSN not set in environment."
        log_info "To enable Sentry error tracking:"
        log_info "  1. Create a Sentry project at https://sentry.io"
        log_info "  2. Get your DSN"
        log_info "  3. Add SENTRY_DSN to your .env file"
        log_info "  4. Install sentry-sdk: pip install sentry-sdk"
    else
        log_info "Sentry DSN found. Error tracking will be enabled."
        
        # Check if sentry-sdk is installed
        if ! python -c "import sentry_sdk" 2>/dev/null; then
            log_warn "sentry-sdk not installed. Installing..."
            pip install sentry-sdk
        fi
    fi
}

setup_logging() {
    log_step "Setting up structured logging..."

    # Set environment variable for JSON logging in production
    if [ "${ENVIRONMENT:-}" = "production" ]; then
        export PRISMIND_LOG_FORMAT=json
        export PRISMIND_LOG_LEVEL=INFO
        log_info "Production logging configured (JSON format)"
    else
        export PRISMIND_LOG_FORMAT=console
        log_info "Development logging configured (console format)"
    fi
}

setup_metrics() {
    log_step "Setting up metrics collection..."

    log_info "Metrics collection is automatically enabled."
    log_info "Metrics endpoints available at:"
    log_info "  - GET /health/metrics - Application metrics"
    log_info "  - GET /health - Comprehensive health check with metrics"
}

create_monitoring_directories() {
    log_step "Creating monitoring directories..."

    mkdir -p logs
    mkdir -p data/metrics
    mkdir -p data/analytics

    log_info "Monitoring directories created"
}

configure_alerts() {
    log_step "Configuring alerting rules..."

    # Alert configuration is handled in the code
    # This script just documents the alert setup
    log_info "Default alert rules configured:"
    log_info "  - High CPU Usage (>80%)"
    log_info "  - High Memory Usage (>85%)"
    log_info "  - Low Disk Space (>90%)"
    log_info "  - Slow API Response (>5s)"
    log_info "  - High Error Rate (>10%)"
    
    log_info "To customize alerts, modify src/monitoring/performance_monitor.py"
}

verify_setup() {
    log_step "Verifying monitoring setup..."

    # Check Python imports
    if python -c "from src.monitoring import get_metrics_collector, get_error_tracker, get_performance_monitor" 2>/dev/null; then
        log_info "Monitoring modules can be imported ✓"
    else
        log_error "Failed to import monitoring modules"
        return 1
    fi

    # Check if health endpoints exist
    if [ -f "services/api/app.py" ]; then
        if grep -q "/health" services/api/app.py; then
            log_info "Health check endpoints found ✓"
        else
            log_warn "Health check endpoints not found in services/api/app.py"
        fi
    fi

    log_info "Monitoring setup verification complete"
}

main() {
    log_info "Setting up monitoring for Prismind..."

    check_env_file
    setup_sentry
    setup_logging
    setup_metrics
    create_monitoring_directories
    configure_alerts
    verify_setup

    log_info ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Monitoring setup complete!"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info ""
    log_info "Next steps:"
    log_info "  1. Configure SENTRY_DSN in .env (optional)"
    log_info "  2. Set ENVIRONMENT=production for JSON logging"
    log_info "  3. Access health endpoints at http://localhost:8000/health"
    log_info "  4. Check metrics at http://localhost:8000/health/metrics"
    log_info ""
}

main






