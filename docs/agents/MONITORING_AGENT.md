# Monitoring Agent Documentation

## Overview

The Monitoring Agent is a centralized system health monitoring, performance metrics collection, and alerting agent that inherits from `BaseAgent`. It provides comprehensive observability for the BEYONDLINES system.

## Features

### System Health Monitoring

- **Agent Health**: Monitors all registered agents in the system
- **Service Health**: Monitors external services (Supabase, Redis, Database)
- **System Resources**: Monitors CPU, memory, and disk usage
- **Health Status Aggregation**: Aggregates health status from all components

### Performance Metrics Collection

- **Agent Metrics**: Collects metrics from all agents (tasks, execution times, errors)
- **Application Metrics**: Collects application-level metrics (active agents, task counts)
- **Database Metrics**: Collects database statistics (post counts, activity)
- **Business Metrics**: Collects business-level metrics (alerts sent, health checks)

### Alerting

- **Multiple Channels**: Supports email, Slack, and Telegram alerts
- **Threshold-Based**: Automatically triggers alerts when thresholds are breached
- **Cooldown Mechanism**: Prevents alert spam with configurable cooldown periods
- **Alert Levels**: Supports info, warning, and critical alert levels

### Dashboard Data Aggregation

- **Real-Time Metrics**: Provides current system state
- **Historical Metrics**: Maintains historical data for trend analysis
- **Trend Analysis**: Calculates trends for system resources and performance

## Architecture

### Class Structure

```
MonitoringAgent (BaseAgent)
├── AlertChannel
│   ├── Email alerts
│   ├── Slack alerts
│   └── Telegram alerts
├── Health Monitoring
│   ├── Agent health checks
│   ├── Service health checks
│   └── System resource monitoring
├── Metrics Collection
│   ├── Agent metrics
│   ├── Application metrics
│   ├── Database metrics
│   └── Business metrics
└── Dashboard Aggregation
    ├── Real-time data
    ├── Historical data
    └── Trend analysis
```

### Dependencies

- `BaseAgent`: Inherits from base agent framework
- `AgentRegistry`: Uses registry to discover and monitor agents
- `psutil`: System resource monitoring
- `httpx`: HTTP requests for service health checks and alerts
- `smtplib`: Email alert delivery

## Configuration

Configuration is loaded from `src/agents/config/monitoring_agent.yaml`:

```yaml
# Monitoring intervals (in seconds)
monitoring_interval_seconds: 60
health_check_interval_seconds: 30

# Alert thresholds
alert_thresholds:
  cpu_percent: 80.0
  memory_percent: 80.0
  disk_percent: 90.0
  agent_failure_count: 3
  service_failure_count: 3
  response_time_ms: 1000.0

# Alert cooldown (seconds)
alert_cooldown_seconds: 300

# Alert channels
alert_channels:
  email:
    enabled: false
    smtp_server: smtp.gmail.com
    smtp_port: 587
    smtp_user: ""
    smtp_password: ""
    to_email: ""
  
  slack:
    enabled: false
    webhook_url: ""
  
  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""
```

## Usage

### Basic Initialization

```python
from src.agents.monitoring_agent import MonitoringAgent
from src.agents.registry import get_registry

# Create and register agent
registry = get_registry()
agent = MonitoringAgent(
    agent_id="monitoring_agent",
    agent_name="Monitoring Agent",
    config_path="src/agents/config/monitoring_agent.yaml"
)

registry.register(agent)
await agent.initialize()
```

### Executing Tasks

```python
# Health check
result = await agent.execute({"action": "health_check"})

# Collect metrics
result = await agent.execute({"action": "collect_metrics"})

# Get dashboard data
result = await agent.execute({
    "action": "get_dashboard_data",
    "time_range": "1h"  # or "24h", "7d", etc.
})

# Get specific agent health
result = await agent.execute({
    "action": "get_agent_health",
    "agent_id": "some_agent"
})

# Get specific service health
result = await agent.execute({
    "action": "get_service_health",
    "service_name": "supabase"
})

# Trigger manual alert
result = await agent.execute({
    "action": "trigger_alert",
    "level": "warning",
    "title": "Manual Alert",
    "message": "This is a test alert",
    "metadata": {"key": "value"}
})
```

### Health Check

```python
health = await agent.health_check()
# Returns:
# {
#   "agent_id": "monitoring_agent",
#   "status": "idle",
#   "healthy": true,
#   "monitoring_active": true,
#   "metrics_collected": {...},
#   "alert_channels": 2,
#   ...
# }
```

## Monitoring Loop

The monitoring agent runs a continuous monitoring loop that:

1. Performs periodic health checks (every `health_check_interval_seconds`)
2. Collects metrics from all agents and services
3. Checks alert thresholds
4. Triggers alerts when thresholds are breached
5. Stores metrics in history for dashboard aggregation

The loop runs in the background and can be stopped by calling `shutdown()`.

## Metrics Storage

Metrics are stored in memory using `deque` collections with configurable maximum sizes:

- `agent_health`: Health check results (max 1000)
- `service_health`: Service health checks (max 1000)
- `system_resources`: System resource snapshots (max 1000)
- `performance`: Performance metrics (max 1000)
- `alerts`: Alert history (max 500)

## Alert System

### Alert Levels

- **info**: Informational alerts
- **warning**: Warning alerts (threshold breaches)
- **critical**: Critical alerts (service failures, resource exhaustion)

### Alert Channels

#### Email

Configure SMTP settings in the config file:

```yaml
alert_channels:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    smtp_user: your-email@gmail.com
    smtp_password: your-password
    to_email: recipient@example.com
```

#### Slack

Configure webhook URL:

```yaml
alert_channels:
  slack:
    enabled: true
    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### Telegram

Configure bot token and chat ID:

```yaml
alert_channels:
  telegram:
    enabled: true
    bot_token: YOUR_BOT_TOKEN
    chat_id: YOUR_CHAT_ID
```

Or use environment variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### Alert Cooldown

To prevent alert spam, alerts with the same `alert_key` are suppressed for `alert_cooldown_seconds` (default: 300 seconds / 5 minutes).

## Dashboard Data

### Time Ranges

Supported time range formats:
- `30m`: 30 minutes
- `1h`: 1 hour
- `24h`: 24 hours
- `7d`: 7 days

### Dashboard Structure

```python
{
    "time_range": "1h",
    "timestamp": 1234567890.0,
    "real_time": {
        "system_resources": {...},
        "agent_health": {...}
    },
    "historical": {
        "system_resources": [...],
        "performance": [...],
        "agent_health": [...]
    },
    "trends": {
        "cpu": {
            "current": 50.0,
            "average": 45.0,
            "trend": "increasing"
        },
        "memory": {...}
    }
}
```

## Performance Benchmarks

The monitoring agent is designed to meet the following performance requirements:

- **Metrics collection latency**: < 100ms
- **Health check latency**: < 500ms
- **Alert delivery latency**: < 1 second

## Error Handling

The monitoring agent includes comprehensive error handling:

- Service connection failures are logged but don't stop monitoring
- Individual agent health check failures are isolated
- Monitoring loop continues even if individual checks fail
- All errors are logged with full stack traces

## Integration with Agent Framework

The monitoring agent integrates with the agent framework:

- **Registration**: Registers with `AgentRegistry`
- **Health Checks**: Uses `BaseAgent.health_check()` for all agents
- **Metrics**: Collects metrics from all agents via `get_metrics()`
- **Events**: Publishes events for status changes and alerts

## Testing

### Unit Tests

Run unit tests:

```bash
pytest tests/agents/test_monitoring_agent.py -v
```

### Integration Tests

Run integration tests:

```bash
pytest tests/agents/integration/test_monitoring_flow.py -v
```

### Coverage

Target coverage: 95%+

```bash
pytest tests/agents/test_monitoring_agent.py --cov=src/agents/monitoring_agent --cov-report=html
```

## Troubleshooting

### Monitoring Loop Not Running

- Check that `initialize()` was called successfully
- Verify `_monitoring_task` is not None
- Check logs for initialization errors

### Alerts Not Sending

- Verify alert channels are enabled in config
- Check channel configuration (credentials, URLs)
- Review alert cooldown settings
- Check logs for alert delivery errors

### High Resource Usage

- Adjust `monitoring_interval_seconds` to reduce frequency
- Reduce `max_history_size` in metrics retention
- Review number of agents being monitored

### Service Health Checks Failing

- Verify service connections are properly initialized
- Check service credentials and URLs
- Review timeout settings
- Check network connectivity

## Future Enhancements

Potential future enhancements:

- Persistent metrics storage (database)
- Advanced alert routing and filtering
- Custom metric collectors
- Webhook endpoints for external integrations
- Grafana/Prometheus integration
- Distributed monitoring across multiple instances



