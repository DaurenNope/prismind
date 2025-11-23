#!/bin/bash
# Environment validation script for Prismind
# Validates that all required environment variables are set correctly

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ENV_FILE="${1:-.env}"
ERRORS=0
WARNINGS=0

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((ERRORS++))
}

log_check() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

# Load environment file
if [ -f "$ENV_FILE" ]; then
    log_info "Loading environment from $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
else
    log_error "Environment file not found: $ENV_FILE"
    exit 1
fi

# Required variables
REQUIRED_VARS=(
    "SUPABASE_URL"
    "SUPABASE_SERVICE_ROLE_KEY"
)

# Optional but recommended variables
RECOMMENDED_VARS=(
    "SUPABASE_KEY"
    "MISTRAL_API_KEY"
    "GEMINI_API_KEY"
)

# Validate required variables
log_check "Checking required variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        log_error "Required variable not set: $var"
    elif [[ "${!var}" == *"your_"* ]] || [[ "${!var}" == *"YOUR_"* ]]; then
        log_error "Variable $var appears to have placeholder value: ${!var}"
    else
        log_info "✓ $var is set"
    fi
done

# Validate recommended variables
log_check "Checking recommended variables..."
for var in "${RECOMMENDED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        log_warn "Recommended variable not set: $var"
    elif [[ "${!var}" == *"your_"* ]] || [[ "${!var}" == *"YOUR_"* ]]; then
        log_warn "Variable $var appears to have placeholder value: ${!var}"
    else
        log_info "✓ $var is set"
    fi
done

# Validate URL formats
log_check "Validating URL formats..."
if [ -n "${SUPABASE_URL:-}" ]; then
    if [[ ! "${SUPABASE_URL}" =~ ^https?:// ]]; then
        log_error "SUPABASE_URL must be a valid URL (http:// or https://)"
    fi
fi

if [ -n "${REDIS_URL:-}" ]; then
    if [[ ! "${REDIS_URL}" =~ ^redis:// ]]; then
        log_warn "REDIS_URL should start with redis://"
    fi
fi

if [ -n "${OLLAMA_URL:-}" ]; then
    if [[ ! "${OLLAMA_URL}" =~ ^http:// ]]; then
        log_warn "OLLAMA_URL should start with http://"
    fi
fi

# Validate numeric values
log_check "Validating numeric values..."
if [ -n "${API_PORT:-}" ]; then
    if ! [[ "${API_PORT}" =~ ^[0-9]+$ ]]; then
        log_error "API_PORT must be a number"
    fi
fi

if [ -n "${GATEWAY_PORT:-}" ]; then
    if ! [[ "${GATEWAY_PORT}" =~ ^[0-9]+$ ]]; then
        log_error "GATEWAY_PORT must be a number"
    fi
fi

# Validate boolean values
log_check "Validating boolean values..."
BOOLEAN_VARS=(
    "ENABLE_SQLITE_CACHE"
    "ENABLE_THREADS"
    "ENABLE_ANALYSIS"
    "SUPABASE_ENABLED"
)

for var in "${BOOLEAN_VARS[@]}"; do
    if [ -n "${!var:-}" ]; then
        value="${!var}"
        if [[ ! "$value" =~ ^(true|false|1|0|yes|no)$ ]]; then
            log_warn "Variable $var should be a boolean (true/false), got: $value"
        fi
    fi
done

# Check for Sentry configuration
log_check "Checking error tracking configuration..."
if [ -z "${SENTRY_DSN:-}" ]; then
    log_warn "SENTRY_DSN not set. Error tracking will be disabled."
else
    if [[ "${SENTRY_DSN}" =~ ^https://.*@.*sentry\.io ]]; then
        log_info "✓ SENTRY_DSN format looks valid"
    else
        log_warn "SENTRY_DSN format may be invalid"
    fi
fi

# Validate environment
log_check "Checking environment setting..."
if [ -z "${ENVIRONMENT:-}" ]; then
    log_warn "ENVIRONMENT not set. Defaulting to 'development'"
else
    case "${ENVIRONMENT}" in
        development|staging|production)
            log_info "✓ ENVIRONMENT is set to: ${ENVIRONMENT}"
            ;;
        *)
            log_warn "ENVIRONMENT should be one of: development, staging, production. Got: ${ENVIRONMENT}"
            ;;
    esac
fi

# Check for placeholder values
log_check "Checking for placeholder values..."
env | grep -E '^[A-Z_]+=' | while IFS='=' read -r key value; do
    if [[ "$value" == *"your_"* ]] || [[ "$value" == *"YOUR_"* ]] || [[ "$value" == *"example"* ]]; then
        log_warn "Variable $key may have placeholder value: ${value:0:50}..."
    fi
done

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Errors:   $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    log_info "✓ Environment validation passed!"
    
    if [ $WARNINGS -gt 0 ]; then
        log_warn "Some warnings were found. Review them above."
    fi
    
    exit 0
else
    log_error "Environment validation failed with $ERRORS error(s)"
    exit 1
fi






