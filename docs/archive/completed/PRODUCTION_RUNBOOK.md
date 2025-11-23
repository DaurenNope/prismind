# Production Runbook

**Prismind - Production Operations Guide**

This runbook provides procedures for operating Prismind in production, including common issues, health checks, and troubleshooting.

---

## Table of Contents

1. [Health Check Procedures](#health-check-procedures)
2. [Common Issues and Solutions](#common-issues-and-solutions)
3. [Logging Locations](#logging-locations)
4. [Backup Procedures](#backup-procedures)
5. [Service Restart Procedures](#service-restart-procedures)
6. [Emergency Procedures](#emergency-procedures)

---

## Health Check Procedures

### Quick Health Check

```bash
# Check all services are running
docker compose ps

# Quick health endpoint check
curl -s http://localhost:8000/health/live | jq
curl -s http://localhost:8000/health/ready | jq
curl -s http://localhost:8000/health | jq '.status'

# Check gateway
curl -s http://localhost:8080/health | jq
```

### Comprehensive Health Check

```bash
# Run automated health check script
./scripts/deploy/test-docker.sh

# Manual comprehensive check
curl -s http://localhost:8000/health | jq '{
  status: .status,
  redis: .checks.redis.status,
  database: .checks.database.status,
  queues: .checks.job_queues,
  resources: .checks.system_resources
}'
```

### Health Check Interpretation

**Status Values:**
- `healthy`: All systems operational
- `degraded`: Some systems degraded but serviceable
- `unhealthy`: Critical systems failing

**Component Status:**
- `healthy`: Component working correctly
- `degraded`: Component responding but with issues
- `error`: Component failing

### Response Times

Expected response times:
- `/health/live`: < 100ms (should be instant)
- `/health/ready`: < 500ms (includes dependency checks)
- `/health`: < 2s (comprehensive checks)

---

## Common Issues and Solutions

### Issue: Service Won't Start

**Symptoms:**
- Container exits immediately
- Health checks fail

**Diagnosis:**
```bash
# Check logs
docker compose logs <service-name>

# Check container status
docker compose ps

# Check resource limits
docker stats
```

**Solutions:**

1. **Environment Variable Issues**
   ```bash
   # Validate environment
   ./scripts/deploy/validate-env.sh .env
   
   # Check specific service env
   docker compose config | grep -A 20 <service-name>
   ```

2. **Port Conflicts**
   ```bash
   # Check if ports are in use
   lsof -i :8000
   lsof -i :8080
   
   # Change ports in docker-compose.yml if needed
   ```

3. **Resource Exhaustion**
   ```bash
   # Check memory/CPU usage
   docker stats
   
   # Increase limits in docker-compose.yml
   # Or restart system
   ```

### Issue: High Error Rate

**Symptoms:**
- Health check shows `degraded` or `unhealthy`
- Error logs increasing
- Metrics show high error rate

**Diagnosis:**
```bash
# Check recent errors
docker compose logs --tail=100 --since=10m api | grep -i error

# Check metrics
curl -s http://localhost:8000/health/metrics | jq '.database_performance.by_operation'

# Check Sentry (if configured)
# Visit Sentry dashboard
```

**Solutions:**

1. **Database Connection Issues**
   ```bash
   # Test database connection
   docker compose exec api python -c "
   from src.services.new_database_manager import get_database_manager
   db = get_database_manager()
   print('DB connected' if db else 'DB failed')
   "
   
   # Check Supabase status
   curl -I https://api.supabase.co/health
   ```

2. **Redis Connection Issues**
   ```bash
   # Test Redis
   docker compose exec redis redis-cli ping
   
   # Check Redis logs
   docker compose logs redis
   ```

3. **Worker Queue Backlog**
   ```bash
   # Check queue status
   docker compose exec api python -c "
   from services.common.job_queue import get_queue
   q = get_queue('publisher')
   print(f'Pending: {len(q)}')
   "
   
   # Restart workers if backlogged
   docker compose restart worker-publisher
   ```

### Issue: Slow Performance

**Symptoms:**
- API response times > 5s
- Health checks timing out
- High CPU/memory usage

**Diagnosis:**
```bash
# Check performance metrics
curl -s http://localhost:8000/health/metrics | jq '.database_performance'

# Check resource usage
docker stats --no-stream

# Check slow queries (if database supports it)
# In Supabase SQL Editor: Check pg_stat_statements
```

**Solutions:**

1. **Database Performance**
   ```bash
   # Check database connection pool
   # Increase pool size in configuration if needed
   
   # Check for missing indexes
   # Review query performance in Supabase dashboard
   ```

2. **Resource Limits**
   ```bash
   # Increase resource limits in docker-compose.yml
   # Restart services
   docker compose up -d --force-recreate
   ```

3. **Worker Overload**
   ```bash
   # Scale workers
   docker compose up -d --scale worker-publisher=3
   ```

### Issue: Workers Not Processing Jobs

**Symptoms:**
- Queue backlog increasing
- No job processing logs
- Jobs stuck in "queued" status

**Diagnosis:**
```bash
# Check worker logs
docker compose logs worker-publisher --tail=50

# Check queue status
docker compose exec api python -c "
from services.common.job_queue import get_queue
q = get_queue('publisher')
print(f'Queue length: {len(q)}')
print(f'Failed jobs: {q.failed_job_registry.count}')
"
```

**Solutions:**

1. **Restart Workers**
   ```bash
   docker compose restart worker-publisher worker-rewriter
   ```

2. **Check Worker Configuration**
   ```bash
   # Verify WORKER_QUEUE is set correctly
   docker compose exec worker-publisher env | grep WORKER_QUEUE
   ```

3. **Clear Failed Jobs**
   ```bash
   # Access Redis CLI
   docker compose exec redis redis-cli
   
   # Clear failed jobs (careful - this removes all failed jobs)
   # Better: Fix root cause and requeue specific jobs
   ```

---

## Logging Locations

### Docker Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs api
docker compose logs worker-publisher

# Follow logs
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api

# Since timestamp
docker compose logs --since=10m api

# Time range
docker compose logs --since="2025-01-01T10:00:00" --until="2025-01-01T11:00:00" api
```

### Log Files (If Not Using Docker)

```bash
# Application logs
tail -f logs/beyondlines_$(date +%Y%m%d).log

# Performance logs
tail -f logs/performance_$(date +%Y%m%d).log

# Error logs
grep -i error logs/*.log | tail -50
```

### Log Format (Production)

In production, logs are in JSON format:

```json
{
  "timestamp": "2025-01-01T10:00:00Z",
  "level": "ERROR",
  "module": "beyondlines.api",
  "message": "Database connection failed",
  "correlation_id": "abc-123-def",
  "context": {...}
}
```

### Searching Logs

```bash
# Search for errors
docker compose logs | grep -i error

# Search by correlation ID
docker compose logs | grep "abc-123-def"

# Search by time
docker compose logs --since=1h | grep -i error

# JSON log parsing (if using jq)
docker compose logs api | jq 'select(.level=="ERROR")'
```

---

## Backup Procedures

### Database Backup

**Supabase (Cloud):**
- Supabase automatically backs up daily
- Manual backup: Use Supabase dashboard → Settings → Database → Backup
- Export data: Use Supabase SQL Editor or API

**SQLite (Local Cache):**
```bash
# Backup SQLite database
docker compose exec api python -c "
import shutil
from pathlib import Path
db_path = Path('data/beyondlines.db')
if db_path.exists():
    shutil.copy(db_path, f'backups/beyondlines_{Path(__file__).stem}.db.backup')
"

# Or manually
cp data/beyondlines.db backups/beyondlines_$(date +%Y%m%d).db
```

### Configuration Backup

```bash
# Backup environment file
cp .env backups/env_backup_$(date +%Y%m%d_%H%M%S)

# Backup docker-compose.yml
cp docker-compose.yml backups/docker-compose_$(date +%Y%m%d).yml
```

### Automated Backup Script

Create `scripts/deploy/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup environment
cp .env "$BACKUP_DIR/.env"

# Backup configuration
cp docker-compose.yml "$BACKUP_DIR/"

# Backup logs (last 7 days)
cp -r logs "$BACKUP_DIR/" 2>/dev/null || true

echo "Backup completed: $BACKUP_DIR"
```

### Restore Procedures

**Database Restore:**
1. Use Supabase dashboard → Database → Backup → Restore
2. Or use pg_restore if you have a dump file

**Configuration Restore:**
```bash
# Restore environment file
cp backups/env_backup_YYYYMMDD_HHMMSS .env

# Restart services
docker compose restart
```

---

## Service Restart Procedures

### Graceful Restart (Zero Downtime)

```bash
# Restart specific service
docker compose restart api

# Rolling restart (one at a time)
docker compose restart api
sleep 10
docker compose restart api-gateway

# Restart all services
docker compose restart
```

### Force Restart

```bash
# Stop and start (not graceful)
docker compose stop api
docker compose start api

# Recreate container
docker compose up -d --force-recreate api
```

### Full Service Restart

```bash
# Stop all services
docker compose down

# Start all services
docker compose up -d

# Verify
./scripts/deploy/test-docker.sh
```

---

## Emergency Procedures

### Complete System Failure

1. **Check Status**
   ```bash
   docker compose ps
   docker compose logs --tail=100
   ```

2. **Restart Infrastructure**
   ```bash
   docker compose restart redis ollama
   sleep 10
   docker compose restart api api-gateway
   ```

3. **If Still Failing**
   ```bash
   # Complete restart
   docker compose down
   docker compose up -d
   ```

### Database Outage

1. **Verify Database Status**
   ```bash
   # Check Supabase status page
   curl -I https://api.supabase.co/health
   ```

2. **Enable Local Cache (if configured)**
   ```bash
   # Set in .env
   ENABLE_SQLITE_CACHE=true
   docker compose restart api
   ```

3. **Service Degradation**
   - System will operate in degraded mode
   - Writes will queue until database returns
   - Monitor logs for connection attempts

### High Resource Usage

1. **Immediate Actions**
   ```bash
   # Check resource usage
   docker stats
   
   # Identify heavy services
   docker compose top
   ```

2. **Scale Down**
   ```bash
   # Reduce workers
   docker compose stop worker-rewriter
   
   # Or scale
   docker compose up -d --scale worker-publisher=1
   ```

3. **Restart Services**
   ```bash
   docker compose restart
   ```

---

## Monitoring Checklist

Daily checks:
- [ ] All services healthy
- [ ] No error spikes in logs
- [ ] Resource usage normal
- [ ] Queue backlog reasonable

Weekly checks:
- [ ] Review error logs
- [ ] Check backup status
- [ ] Review performance metrics
- [ ] Update dependencies (if needed)

---

## Support Contacts

- **On-Call Engineer**: [Contact Info]
- **Database Admin**: [Contact Info]
- **DevOps Team**: [Contact Info]
- **Sentry Dashboard**: https://sentry.io/...
- **Supabase Dashboard**: https://supabase.com/dashboard/...

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0






