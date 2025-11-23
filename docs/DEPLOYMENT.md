# Production Deployment Guide

**Prismind - Production Deployment Documentation**

This guide covers deploying Prismind to production using Docker.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Rollback Procedures](#rollback-procedures)
6. [Post-Deployment Verification](#post-deployment-verification)

---

## Prerequisites

### System Requirements

- **Docker**: Version 20.10+ and Docker Compose 2.0+
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **Disk**: Minimum 20GB free space
- **Network**: Internet access for AI services and database connections

### Software Requirements

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git (for cloning repository)
- `curl` and `jq` (for health checks)

### External Services

- **Supabase**: Database (required)
  - Create project at https://supabase.com
  - Get URL, anon key, and service role key
- **Redis**: Job queue (included in docker-compose)
- **AI Services** (optional but recommended):
  - Mistral AI API key
  - Google Gemini API key
  - Or local Ollama instance

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker compose version

# Check system resources
free -h  # Linux
df -h    # Disk space

# Check network connectivity
curl -I https://api.mistral.ai
```

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd prismind
```

### 2. Create Environment File

```bash
# Copy production template
cp .env.production.example .env

# Or create from scratch
nano .env
```

### 3. Configure Environment Variables

Required variables (minimum for deployment):

```bash
# Environment
ENVIRONMENT=production
PRISMIND_LOG_FORMAT=json
PRISMIND_LOG_LEVEL=INFO

# Database [REQUIRED]
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Redis [REQUIRED]
REDIS_URL=redis://redis:6379/0

# AI Services [OPTIONAL but recommended]
MISTRAL_API_KEY=your_key
GEMINI_API_KEY=your_key

# Monitoring [OPTIONAL]
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### 4. Validate Configuration

```bash
# Run validation script
./scripts/deploy/validate-env.sh .env

# Or manually validate
python -c "from src.utils.config_validator import validate_config_at_startup; validate_config_at_startup()"
```

---

## Docker Deployment

### Option 1: Quick Start (All Services)

```bash
# Build all services
./scripts/deploy/build.sh --compose

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Option 2: Step-by-Step Deployment

#### 1. Build Services

```bash
# Build all services
docker compose build

# Or build individual services
docker compose build api
docker compose build api-gateway
docker compose build worker-publisher
```

#### 2. Start Infrastructure Services

```bash
# Start Redis and Ollama first
docker compose up -d redis ollama

# Wait for services to be healthy
docker compose ps
```

#### 3. Start Application Services

```bash
# Start API services
docker compose up -d api api-gateway

# Start workers
docker compose up -d worker-publisher worker-rewriter worker-collector-threads worker-collector-twitter

# Verify all services are running
docker compose ps
```

#### 4. Verify Health Checks

```bash
# Run test script
./scripts/deploy/test-docker.sh

# Or manually check
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8080/health
```

### Option 3: Production Deployment with Updates

```bash
# Pull latest code
git pull origin main

# Build new images
docker compose build

# Stop old services (zero-downtime with proper load balancer config)
docker compose stop api api-gateway

# Start new services
docker compose up -d api api-gateway

# Verify deployment
./scripts/deploy/test-docker.sh

# Restart workers (optional, can do rolling restart)
docker compose restart worker-publisher worker-rewriter
```

---

## Manual Deployment

If you prefer not to use Docker, follow these steps:

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip redis-server

# macOS
brew install python@3.11 redis
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers (for workers)
playwright install chromium
```

### 3. Set Up Redis

```bash
# Start Redis
redis-server --daemonize yes

# Or with systemd
sudo systemctl start redis
sudo systemctl enable redis
```

### 4. Configure Environment

```bash
# Copy environment file
cp .env.production.example .env

# Edit with your values
nano .env
```

### 5. Start Services

```bash
# Terminal 1: API Server
source .venv/bin/activate
uvicorn services.api.app:app --host 0.0.0.0 --port 8000 --workers 2

# Terminal 2: API Gateway
source .venv/bin/activate
python services/gateway/run_gateway.py

# Terminal 3: Worker (Publisher)
source .venv/bin/activate
export WORKER_QUEUE=publisher
python services/worker/run_worker.py

# Terminal 4+: Additional Workers
export WORKER_QUEUE=rewriter
python services/worker/run_worker.py
```

### 6. Use Process Manager (Production)

```bash
# Install PM2 (Node.js process manager for Python)
npm install -g pm2

# Create PM2 ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [
    {
      name: 'prismind-api',
      script: 'uvicorn',
      args: 'services.api.app:app --host 0.0.0.0 --port 8000 --workers 2',
      interpreter: 'python3',
      cwd: '/path/to/prismind',
      env: {
        ENVIRONMENT: 'production',
      },
    },
    {
      name: 'prismind-gateway',
      script: 'python',
      args: 'services/gateway/run_gateway.py',
      interpreter: 'python3',
      cwd: '/path/to/prismind',
    },
  ],
};
EOF

# Start services
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

---

## Rollback Procedures

### Docker Rollback

```bash
# Stop current services
docker compose stop api api-gateway

# Tag previous image (if using tags)
docker tag prismind-api:latest prismind-api:previous

# Checkout previous version
git checkout <previous-commit-hash>

# Rebuild and restart
docker compose build api api-gateway
docker compose up -d api api-gateway

# Verify
./scripts/deploy/test-docker.sh
```

### Database Rollback

If database migrations need to be rolled back:

```bash
# Connect to Supabase SQL Editor
# Run reverse migration scripts

# Example (if you have migration rollback scripts)
psql $DATABASE_URL < migrations/rollback_<migration_name>.sql
```

### Manual Service Rollback

```bash
# Stop services
pm2 stop all  # or docker compose stop

# Restore from backup
git checkout <previous-tag>

# Rebuild and restart
./scripts/deploy/build.sh
docker compose up -d  # or pm2 start all
```

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# Liveness probe
curl http://localhost:8000/health/live

# Readiness probe
curl http://localhost:8000/health/ready

# Comprehensive health
curl http://localhost:8000/health | jq

# Gateway health
curl http://localhost:8080/health
```

### 2. Service Status

```bash
# Check all containers
docker compose ps

# Check logs for errors
docker compose logs --tail=100 api
docker compose logs --tail=100 worker-publisher

# Check resource usage
docker stats
```

### 3. Functional Tests

```bash
# Test API endpoints
curl -X POST http://localhost:8000/jobs/collect \
  -H "Content-Type: application/json" \
  -d '{"platform": "threads", "force_once": false}'

# Check job status
curl http://localhost:8000/jobs/<job_id>

# Test metrics
curl http://localhost:8000/health/metrics | jq
```

### 4. Monitoring Verification

```bash
# Check error tracking (if Sentry configured)
# Visit Sentry dashboard and verify events are being received

# Check logs (should be JSON format)
docker compose logs api | jq -r '.message' | head -20

# Check metrics collection
curl http://localhost:8000/health/metrics
```

---

## Common Issues

### Services Won't Start

1. Check environment variables are set correctly
2. Verify dependencies (Redis, Supabase) are accessible
3. Check logs: `docker compose logs <service-name>`

### Health Checks Failing

1. Verify Redis is running and accessible
2. Check database connection credentials
3. Review service logs for errors

### High Resource Usage

1. Adjust resource limits in `docker-compose.yml`
2. Reduce worker concurrency
3. Check for memory leaks in logs

---

## Security Checklist

- [ ] All secrets stored in environment variables (not in code)
- [ ] `.env` file is in `.gitignore`
- [ ] Database credentials are secure (service role key)
- [ ] API keys are rotated regularly
- [ ] Network is properly firewalled
- [ ] SSL/TLS is configured (if using reverse proxy)
- [ ] Regular security updates applied

---

## Next Steps

After deployment:

1. Set up monitoring dashboards (see [MONITORING.md](MONITORING.md))
2. Configure alerting (see [PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md))
3. Schedule backups
4. Document any custom configurations

---

## Support

For issues or questions:

1. Check [PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md) for common issues
2. Review logs: `docker compose logs`
3. Check health endpoints: `/health`
4. Open an issue on GitHub

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0






