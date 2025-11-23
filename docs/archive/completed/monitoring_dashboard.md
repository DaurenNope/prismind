# System Monitoring Dashboard

## Overview

The Prismind System Monitoring Dashboard provides real-time visibility into system health, worker status, and posting metrics.

## Usage

### Running the Monitor

```bash
python main.py monitor
```

Or directly:

```bash
python scripts/monitor_system.py
```

### Features

The monitoring dashboard displays:

- **Worker Status**: Whether the publisher worker is running or stopped
- **Due Posts**: Count of posts scheduled and ready to be published
- **Posted (24h)**: Number of posts published in the last 24 hours
- **Active Agents**: Number of active agents in the system
- **CPU Usage**: Current CPU utilization percentage
- **Memory Usage**: Current memory utilization percentage
- **System Health**: Overall system health status (healthy/degraded)

### Update Frequency

The dashboard updates every **5 seconds** automatically.

### Stopping the Monitor

Press `Ctrl+C` to stop the monitoring dashboard.

## Components

### Monitoring Script

**Location**: `scripts/monitor_system.py`

The script uses:
- `MimesisDB`: Database operations for due posts and recent posts
- `PublisherWorker`: Worker status checking
- `MonitoringAgent`: System health and metrics collection

### Integration

The monitor command is integrated into `main.py`:

```bash
python main.py monitor
```

## Metrics Explained

### Worker Status

- **✅ RUNNING**: Publisher worker is active and processing scheduled posts
- **❌ STOPPED**: Publisher worker is not running

### Due Posts

Posts that are scheduled and past their scheduled time, ready to be published.

### Posted (24h)

Posts that have been successfully published in the last 24 hours, retrieved from the `posted_content` table.

### Active Agents

Number of agents registered in the agent registry that are currently active.

### System Resources

- **CPU**: Current CPU usage percentage (updated every 5 seconds)
- **Memory**: Current memory usage percentage

### System Health

Overall health status based on:
- Agent health checks
- Service health (Supabase, Redis, Database)
- System resource thresholds

## Error Handling

The monitoring script includes robust error handling:

- Database connection errors are caught and displayed as warnings
- Monitoring agent initialization failures are handled gracefully
- Missing dependencies (like psutil) are handled with fallbacks
- Network errors don't crash the monitor

## Requirements

- Python 3.11+
- Required packages (from `requirements.txt`):
  - `psutil` (for system metrics)
  - `supabase` (for database access)
  - `asyncio` (built-in)

## Troubleshooting

### Monitor shows "Error getting due posts"

- Check Supabase connection
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` environment variables
- Check network connectivity

### Monitor shows "Error getting health check"

- Monitoring agent may not be initialized
- Check agent registry configuration
- Review logs for detailed error messages

### CPU/Memory not showing

- Ensure `psutil` is installed: `pip install psutil`
- Check if monitoring agent can access system resources

## Example Output

```
======================================================================
Timestamp: 2025-11-23 14:50:31
Worker: ✅ RUNNING
Due Posts: 3
Posted (24h): 12
Active Agents: 5
CPU: 15.3%
Memory: 42.1%
System Health: ✅ HEALTHY
======================================================================
```

## Future Enhancements

Potential improvements:
- Historical metrics graphs
- Alert notifications
- Export metrics to file
- Web-based dashboard
- Customizable update intervals
- Filter by platform or persona

