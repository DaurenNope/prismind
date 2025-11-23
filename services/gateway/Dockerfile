# Multi-stage build for Gateway service
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        python3-dev \
        && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .

# Install base requirements
RUN pip install --user --no-warn-script-location \
        --prefer-binary -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/appuser/.local/bin:$PATH

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY . .

# Set ownership
RUN chown -R appuser:appuser /app

# Set working directory and user
USER appuser

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the API gateway
CMD ["python", "services/gateway/run_gateway.py"]
