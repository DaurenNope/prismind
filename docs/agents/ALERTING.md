# Alerting Configuration Guide

## Overview

The Monitoring Agent supports multiple alert channels for notifying about system issues, threshold breaches, and performance degradation. This guide explains how to configure and use the alerting system.

## Alert Channels

### Email Alerts

Email alerts are sent via SMTP. Configure in `monitoring_agent.yaml`:

```yaml
alert_channels:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    smtp_user: your-email@gmail.com
    smtp_password: your-app-password
    to_email: recipient@example.com
```

#### Gmail Setup

For Gmail, you need to:

1. Enable 2-factor authentication
2. Generate an app-specific password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. Use the generated password in `smtp_password`

#### Other SMTP Providers

**Outlook/Hotmail:**
```yaml
smtp_server: smtp-mail.outlook.com
smtp_port: 587
```

**SendGrid:**
```yaml
smtp_server: smtp.sendgrid.net
smtp_port: 587
smtp_user: apikey
smtp_password: YOUR_SENDGRID_API_KEY
```

**Custom SMTP:**
```yaml
smtp_server: mail.yourdomain.com
smtp_port: 587  # or 465 for SSL
```

### Slack Alerts

Slack alerts are sent via webhooks. Configure in `monitoring_agent.yaml`:

```yaml
alert_channels:
  slack:
    enabled: true
    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### Creating a Slack Webhook

1. Go to https://api.slack.com/apps
2. Create a new app or select existing app
3. Go to "Incoming Webhooks"
4. Activate incoming webhooks
5. Add new webhook to workspace
6. Select channel for alerts
7. Copy webhook URL

#### Slack Alert Format

Slack alerts include:
- Color-coded attachments (green=info, orange=warning, red=critical)
- Alert title and message
- Level and timestamp
- Additional metadata fields

### Telegram Alerts

Telegram alerts are sent via Bot API. Configure in `monitoring_agent.yaml`:

```yaml
alert_channels:
  telegram:
    enabled: true
    bot_token: YOUR_BOT_TOKEN
    chat_id: YOUR_CHAT_ID
```

Or use environment variables:
```bash
export TELEGRAM_BOT_TOKEN=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id
```

#### Creating a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy the bot token
5. Get your chat ID:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find `chat.id` in the response

#### Telegram Alert Format

Telegram alerts include:
- Emoji indicators (ℹ️=info, ⚠️=warning, 🔴=critical)
- HTML-formatted message
- Alert title and details
- Metadata as formatted list

## Alert Levels

### Info

Informational alerts for non-critical events:

```python
await agent.execute({
    "action": "trigger_alert",
    "level": "info",
    "title": "System Update",
    "message": "Monitoring agent restarted"
})
```

### Warning

Warning alerts for threshold breaches:

```python
await agent.execute({
    "action": "trigger_alert",
    "level": "warning",
    "title": "High CPU Usage",
    "message": "CPU usage is 85%",
    "metadata": {"cpu_percent": 85.0}
})
```

### Critical

Critical alerts for service failures:

```python
await agent.execute({
    "action": "trigger_alert",
    "level": "critical",
    "title": "Service Failure",
    "message": "Supabase connection failed",
    "metadata": {"service": "supabase", "error": "Connection timeout"}
})
```

## Alert Thresholds

Configure thresholds in `monitoring_agent.yaml`:

```yaml
alert_thresholds:
  # System resource thresholds (percentages)
  cpu_percent: 80.0
  memory_percent: 80.0
  disk_percent: 90.0
  
  # Failure counts
  agent_failure_count: 3
  service_failure_count: 3
  
  # Performance thresholds
  response_time_ms: 1000.0
```

### Automatic Threshold Alerts

The monitoring agent automatically checks thresholds and triggers alerts:

- **CPU Usage**: Alert when CPU > threshold
- **Memory Usage**: Alert when memory > threshold
- **Disk Usage**: Alert when disk > threshold
- **Agent Failures**: Alert when unhealthy agents > threshold
- **Service Failures**: Alert when unhealthy services > threshold

## Alert Cooldown

Prevent alert spam with cooldown periods:

```yaml
alert_cooldown_seconds: 300  # 5 minutes
```

Alerts with the same `alert_key` are suppressed during the cooldown period.

### Custom Alert Keys

When triggering alerts programmatically, specify an alert key:

```python
await agent._trigger_alert(
    "warning",
    "High CPU",
    "CPU usage is high",
    alert_key="high_cpu"  # Cooldown tracked by this key
)
```

## Alert Examples

### System Resource Alert

```python
# Triggered automatically when CPU exceeds threshold
{
    "level": "warning",
    "title": "High CPU Usage",
    "message": "CPU usage is 85.0% (threshold: 80.0%)",
    "metadata": {
        "cpu_percent": 85.0,
        "threshold": 80.0
    }
}
```

### Service Failure Alert

```python
# Triggered automatically when service fails
{
    "level": "critical",
    "title": "Service Failure",
    "message": "Service(s) unhealthy: supabase",
    "metadata": {
        "unhealthy_services": ["supabase"]
    }
}
```

### Agent Failure Alert

```python
# Triggered automatically when agents fail
{
    "level": "warning",
    "title": "Unhealthy Agents",
    "message": "2 agent(s) are unhealthy",
    "metadata": {
        "unhealthy_count": 2,
        "agents": {...}
    }
}
```

## Testing Alerts

### Test Email Alert

```python
# Configure email channel
agent.config["alert_channels"]["email"]["enabled"] = True
agent.config["alert_channels"]["email"]["smtp_user"] = "test@example.com"
agent.config["alert_channels"]["email"]["to_email"] = "recipient@example.com"

# Trigger test alert
await agent.execute({
    "action": "trigger_alert",
    "level": "info",
    "title": "Test Alert",
    "message": "This is a test alert"
})
```

### Test Slack Alert

```python
# Configure Slack channel
agent.config["alert_channels"]["slack"]["enabled"] = True
agent.config["alert_channels"]["slack"]["webhook_url"] = "https://hooks.slack.com/..."

# Trigger test alert
await agent.execute({
    "action": "trigger_alert",
    "level": "warning",
    "title": "Test Alert",
    "message": "This is a test alert"
})
```

### Test Telegram Alert

```python
# Configure Telegram channel
agent.config["alert_channels"]["telegram"]["enabled"] = True
agent.config["alert_channels"]["telegram"]["bot_token"] = "YOUR_TOKEN"
agent.config["alert_channels"]["telegram"]["chat_id"] = "YOUR_CHAT_ID"

# Trigger test alert
await agent.execute({
    "action": "trigger_alert",
    "level": "info",
    "title": "Test Alert",
    "message": "This is a test alert"
})
```

## Alert History

View alert history:

```python
# Get recent alerts
alerts = agent.metrics_history["alerts"]

# Filter by level
critical_alerts = [a for a in alerts if a["level"] == "critical"]

# Filter by time
from datetime import datetime, timedelta
recent_alerts = [
    a for a in alerts 
    if a["timestamp"] > (time.time() - 3600)  # Last hour
]
```

## Best Practices

### 1. Use Appropriate Alert Levels

- **Info**: Non-critical events, status updates
- **Warning**: Threshold breaches, degraded performance
- **Critical**: Service failures, system outages

### 2. Configure Realistic Thresholds

Set thresholds based on:
- Normal system behavior
- Available resources
- Business requirements

### 3. Enable Multiple Channels

Use multiple channels for redundancy:
- Email for detailed logs
- Slack for team notifications
- Telegram for mobile alerts

### 4. Set Appropriate Cooldowns

- Short cooldowns (60-300s) for critical alerts
- Longer cooldowns (300-600s) for warning alerts
- Very long cooldowns (600-3600s) for info alerts

### 5. Monitor Alert Delivery

Check alert history to ensure alerts are being delivered:

```python
# Check alert delivery rate
total_alerts = len(agent.metrics_history["alerts"])
sent_alerts = sum(1 for a in agent.metrics_history["alerts"] if a["sent"])
delivery_rate = sent_alerts / total_alerts if total_alerts > 0 else 0
```

## Troubleshooting

### Alerts Not Sending

1. **Check channel configuration**:
   ```python
   for channel in agent.alert_channels:
       print(f"{channel.channel_type}: enabled={channel.enabled}")
   ```

2. **Verify credentials**:
   - Email: Test SMTP connection
   - Slack: Test webhook URL
   - Telegram: Test bot token and chat ID

3. **Check logs**:
   ```bash
   grep "alert" logs/monitoring.log
   ```

### Too Many Alerts

1. **Increase cooldown period**:
   ```yaml
   alert_cooldown_seconds: 600  # 10 minutes
   ```

2. **Adjust thresholds**:
   ```yaml
   alert_thresholds:
     cpu_percent: 90.0  # Increase from 80.0
   ```

3. **Disable specific channels**:
   ```yaml
   alert_channels:
     email:
       enabled: false
   ```

### Alert Formatting Issues

1. **Check message length**:
   - Email: No limit
   - Slack: 4000 characters
   - Telegram: 4096 characters

2. **Verify special characters**:
   - Use HTML entities in Telegram
   - Escape special characters in Slack

## Advanced Configuration

### Custom Alert Handlers

Extend `AlertChannel` for custom alert handlers:

```python
from src.agents.monitoring_agent import AlertChannel

class CustomAlertChannel(AlertChannel):
    async def send_alert(self, level, title, message, metadata=None):
        # Custom implementation
        return True

# Register custom channel
agent.alert_channels.append(CustomAlertChannel("custom", {"enabled": True}))
```

### Alert Filtering

Filter alerts before sending:

```python
async def filtered_trigger_alert(agent, level, title, message, metadata=None):
    # Only send critical alerts
    if level != "critical":
        return {"sent": False, "reason": "filtered"}
    
    return await agent._trigger_alert(level, title, message, metadata)
```

## Integration Examples

### Integration with External Systems

```python
# Webhook integration
async def send_webhook_alert(agent, level, title, message):
    webhook_url = "https://your-webhook.com/alerts"
    payload = {
        "level": level,
        "title": title,
        "message": message,
        "timestamp": time.time()
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=payload)
```

### Integration with Monitoring Tools

```python
# Prometheus integration
from prometheus_client import Counter, Gauge

alert_counter = Counter('monitoring_alerts_total', 'Total alerts sent', ['level'])
cpu_gauge = Gauge('system_cpu_percent', 'CPU usage percentage')

# Update metrics
alert_counter.labels(level=level).inc()
cpu_gauge.set(cpu_percent)
```



