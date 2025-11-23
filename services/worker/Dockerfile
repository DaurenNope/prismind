# Multi-stage build for Worker service
# Stage 1: Build dependencies
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy as builder

ENV PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
COPY services/worker/requirements.txt ./services/worker/requirements.txt

# Install base requirements
RUN pip install --user --no-warn-script-location \
        --prefer-binary -r requirements.txt

# Install service-specific requirements
RUN pip install --user --no-warn-script-location \
        --prefer-binary -r services/worker/requirements.txt

# Install Playwright browsers (from base image)
RUN playwright install --with-deps chromium

# Stage 2: Runtime image
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

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

# Copy Playwright browsers from builder
COPY --from=builder /ms-playwright /ms-playwright

# Copy application code
COPY . .

# Set ownership
RUN chown -R appuser:appuser /app

# Set working directory and user
USER appuser

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Health check (simple Python script check)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the worker
ENTRYPOINT ["python", "services/worker/run_worker.py"]
