FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1

WORKDIR /app

# System deps for building wheels (psutil) and SSL
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        python3-dev \
        libssl-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY services/api/requirements.txt ./services/api/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r services/api/requirements.txt

COPY . .
ENV PYTHONPATH=/app

CMD ["uvicorn", "services.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
