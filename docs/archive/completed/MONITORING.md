# Monitoring Guide

**Prismind - Production Monitoring Documentation**

This guide explains the monitoring system, metrics, alerting rules, and dashboard setup for Prismind.

---

## Table of Contents

1. [Monitoring Overview](#monitoring-overview)
2. [Metrics Explanation](#metrics-explanation)
3. [Alerting Rules](#alerting-rules)
4. [Dashboard Setup](#dashboard-setup)
5. [Troubleshooting](#troubleshooting)

---

## Monitoring Overview

Prismind includes comprehensive monitoring with:

- **Application Metrics**: Request counts, response times, error rates
- **Database Metrics**: Query times, connection pool, operation counts
- **Business Metrics**: Posts collected, analyzed, published
- **System Metrics**: CPU, memory, disk usage
- **Error Tracking**: Sentry integration for error aggregation

### Monitoring Components

1. **Performance Monitor** (`src/monitoring/performance_monitor.py`)
   - System metrics collection
   - API performance tracking
   - Operation-level metrics

2. **Metrics Collector** (`src/monitoring/metrics.py`)
   - Application metrics
   - Database metrics
   - Business metrics

3. **Error Tracker** (`src/monitoring/error_tracker.py`)
   - Sentry integration
   - Error context capture
   - Exception tracking

---

## Metrics Explanation

### Application Metrics

**Available via `/health/metrics` endpoint:**

```bash
curl http://localhost:8000/health/metrics | jq
```

**Metrics Categories:**

1. **Request Metrics**
   - `requests_total`: Total API requests
   - `requests_per_second`: Request rate
   - `response_time_avg`: Average response time (ms)
   - `response_time_p95`: 95th percentile response time (ms)
   - `response_time_p99`: 99th percentile response time (ms)

2. **Error Metrics**
   - `errors_total`: Total errors
   - `error_rate`: Error rate percentage
   - `errors_by_endpoint`: Errors grouped by endpoint
   - `errors_by_status_code`: Errors by HTTP status code

3. **Throughput Metrics**
   - `requests_by_method`: Requests by HTTP method (GET, POST, etc.)
   - `requests_by_endpoint`: Requests by API endpoint

### Database Metrics

**Available via `/health/metrics` endpoint:**

```json
{
  "database_performance": {
    "period_hours": 1,
    "total_operations": 1250,
    "by_table": {
      "posts": {
        "operation_count": 800,
        "avg_duration_ms": 12.5,
        "min_duration_ms": 2.1,
        "max_duration_ms": 45.3,
        "error_count": 2,
        "error_rate": 0.25
      }
    },
    "by_operation": {
      "get_posts": {
        "count": 500,
        "avg_duration_ms": 10.2,
        "error_count": 0,
        "error_rate": 0.0
      },
      "add_post": {
        "count": 300,
        "avg_duration_ms": 15.8,
        "error_count": 2,
        "error_rate": 0.67
      }
    }
  }
}
```

**Key Database Metrics:**

- `db_operations_total`: Total database operations
- `db_query_duration_avg`: Average query duration (ms)
- `db_query_duration_p95`: 95th percentile query duration
- `db_connection_pool_size`: Current connection pool size
- `db_connection_pool_active`: Active connections
- `db_errors_total`: Database errors
- `db_errors_by_table`: Errors grouped by table

### Business Metrics

**Collected automatically:**

1. **Collection Metrics**
   - `posts_collected_total`: Total posts collected
   - `posts_collected_by_platform`: Posts by platform (Twitter, Reddit, etc.)
   - `collection_success_rate`: Successful collection rate
   - `collection_duration_avg`: Average collection duration

2. **Analysis Metrics**
   - `posts_analyzed_total`: Total posts analyzed
   - `analysis_success_rate`: Successful analysis rate
   - `analysis_duration_avg`: Average analysis duration

3. **Publishing Metrics**
   - `posts_published_total`: Total posts published
   - `posts_published_by_platform`: Published by platform
   - `publishing_success_rate`: Successful publishing rate
   - `scheduled_posts_count`: Currently scheduled posts

### System Metrics

**Available via `/health` endpoint:**

```json
{
  "checks": {
    "system_resources": {
      "status": "healthy",
      "cpu_percent": 45.2,
      "memory_percent": 62.5,
      "memory_used_mb": 2048,
      "disk_percent": 35.8,
      "disk_free_gb": 128.5
    }
  }
}
```

**System Metrics:**

- `cpu_percent`: CPU usage percentage
- `memory_percent`: Memory usage percentage
- `memory_used_mb`: Memory used in MB
- `disk_percent`: Disk usage percentage
- `disk_free_gb`: Free disk space in GB

---

## Alerting Rules

### Default Alert Rules

Configured in `src/monitoring/performance_monitor.py`:

1. **High CPU Usage**
   - **Threshold**: > 80%
   - **Severity**: Warning
   - **Action**: Monitor and consider scaling

2. **High Memory Usage**
   - **Threshold**: > 85%
   - **Severity**: Warning
   - **Action**: Check for memory leaks, consider scaling

3. **Low Disk Space**
   - **Threshold**: > 90%
   - **Severity**: Critical
   - **Action**: Immediate attention required

4. **Slow API Response**
   - **Threshold**: > 5 seconds average
   - **Severity**: Warning
   - **Action**: Investigate performance bottlenecks

5. **High Error Rate**
   - **Threshold**: > 10%
   - **Severity**: Critical
   - **Action**: Immediate investigation required

### Custom Alert Configuration

```python
from src.monitoring.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()

# Add custom alert rule
monitor.alert_manager.add_alert_rule({
    "name": "Database Slow Queries",
    "metric_type": "db_query_duration",
    "threshold": 1000,  # 1 second
    "operator": "greater_than",
    "severity": "warning",
})
```

### Alert Channels

1. **Sentry Alerts**
   - Configured via `SENTRY_DSN` environment variable
   - Automatic error aggregation
   - Context-aware alerting

2. **Email Alerts** (Optional)
   - Configure via `ALERT_EMAIL_*` environment variables
   - Sends alerts for critical issues

3. **Slack Alerts** (Optional)
   - Configure via `ALERT_SLACK_*` environment variables
   - Real-time notifications

### Alert Severity Levels

- **Critical**: Immediate action required
- **Warning**: Monitor and investigate
- **Info**: Informational only

---

## Dashboard Setup

### Health Check Dashboard

**Endpoint**: `http://localhost:8000/health`

Provides:
- Overall system status
- Component health checks
- System resource usage
- Active alerts
- Metrics summary

**Usage:**
```bash
# Get health status
curl http://localhost:8000/health | jq

# Check specific component
curl http://localhost:8000/health | jq '.checks.redis'
curl http://localhost:8000/health | jq '.checks.database'
```

### Metrics Dashboard

**Endpoint**: `http://localhost:8000/health/metrics`

Provides:
- Application metrics summary
- Database performance metrics
- Business metrics
- Time-series data (last hour)

**Usage:**
```bash
# Get all metrics
curl http://localhost:8000/health/metrics | jq

# Database performance only
curl http://localhost:8000/health/metrics | jq '.database_performance'

# Business metrics only
curl http://localhost:8000/health/metrics | jq '.summary.business_metrics'
```

### Prometheus Integration (Optional)

To expose metrics in Prometheus format:

```python
# Add to services/api/app.py
@app.get("/metrics")
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint"""
    from src.monitoring.metrics import get_metrics_collector
    
    collector = get_metrics_collector()
    summary = collector.get_metrics_summary(hours=1)
    
    # Convert to Prometheus format
    # Implementation would format metrics according to Prometheus spec
    return Response(content=prometheus_format(summary), media_type="text/plain")
```

### Grafana Dashboard Setup

1. **Configure Prometheus Data Source**
   - Point to `/metrics` endpoint
   - Scrape interval: 30s

2. **Create Dashboard Panels**
   - System metrics (CPU, Memory, Disk)
   - API metrics (Request rate, Response time, Error rate)
   - Database metrics (Query duration, Connection pool)
   - Business metrics (Posts collected, Analyzed, Published)

3. **Add Alerts**
   - Configure alert rules matching monitoring alert rules
   - Set up notification channels

---

## Troubleshooting

### Metrics Not Appearing

**Symptoms:**
- `/health/metrics` returns empty data
- Metrics collection not working

**Diagnosis:**
```bash
# Check if metrics collector is initialized
docker compose exec api python -c "
from src.monitoring.metrics import get_metrics_collector
collector = get_metrics_collector()
print('Collector:', collector)
print('Metrics:', len(collector.application_metrics))
"

# Check logs for errors
docker compose logs api | grep -i metric
```

**Solutions:**
1. Verify metrics collection is enabled
2. Check for errors in logs
3. Restart services to reinitialize collectors

### High Metric Collection Overhead

**Symptoms:**
- High CPU usage from metrics collection
- Slow performance

**Solutions:**
1. Reduce metrics collection frequency
2. Limit history size (`max_history` parameter)
3. Disable unnecessary metrics

### Missing Metrics

**Symptoms:**
- Expected metrics not present
- Metrics incomplete

**Solutions:**
1. Check metric collection points in code
2. Verify metrics are being recorded
3. Check metric retention settings

### Sentry Not Receiving Events

**Symptoms:**
- Errors not appearing in Sentry
- Error tracking not working

**Diagnosis:**
```bash
# Check Sentry configuration
docker compose exec api python -c "
from src.monitoring.error_tracker import get_error_tracker
tracker = get_error_tracker()
print('Enabled:', tracker.enabled)
print('Configured:', tracker._configured)
"

# Check environment variables
docker compose exec api env | grep SENTRY
```

**Solutions:**
1. Verify `SENTRY_DSN` is set correctly
2. Check Sentry SDK is installed: `pip install sentry-sdk`
3. Test error tracking manually:
   ```python
   from src.monitoring.error_tracker import get_error_tracker
   tracker = get_error_tracker()
   tracker.capture_exception(Exception("Test error"))
   ```

### Alert Noise

**Symptoms:**
- Too many alerts
- False positives

**Solutions:**
1. Adjust alert thresholds
2. Configure alert cooldowns
3. Add alert suppression rules
4. Fine-tune alert conditions

---

## Best Practices

1. **Regular Monitoring**
   - Check health endpoints daily
   - Review metrics weekly
   - Monitor error rates continuously

2. **Alert Tuning**
   - Start with conservative thresholds
   - Adjust based on actual behavior
   - Avoid alert fatigue

3. **Metrics Retention**
   - Keep detailed metrics for 7 days
   - Aggregate metrics for 30 days
   - Archive older metrics

4. **Dashboard Maintenance**
   - Update dashboards quarterly
   - Add new metrics as needed
   - Remove obsolete metrics

---

## Support

For monitoring issues:
1. Check this guide first
2. Review logs: `docker compose logs`
3. Check health endpoints
4. Open an issue on GitHub

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0






