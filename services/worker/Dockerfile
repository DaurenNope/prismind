FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1
WORKDIR /app

# Toolchain for native wheels (psutil) on aarch64
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY services/worker/requirements.txt ./services/worker/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r services/worker/requirements.txt

COPY . .
ENV PYTHONPATH=/app

ENTRYPOINT ["python", "services/worker/run_worker.py"]
