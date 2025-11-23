# Database Agent Documentation

**Version**: 2.0.0  
**Status**: Production Ready  
**Last Updated**: 2025-01-23

## Overview

The Database Agent is an enhanced database operations layer for BEYONDLINES that inherits from `BaseAgent` and provides advanced features including query optimization, sync management, performance monitoring, and comprehensive health checks.

## Features

### Core Features

- ✅ **BaseAgent Integration**: Inherits from BaseAgent with full lifecycle management
- ✅ **Query Optimization**: Slow query detection, index suggestions, query plan analysis
- ✅ **Sync Management**: SQLite ↔ Supabase sync with conflict resolution
- ✅ **Performance Monitoring**: Query performance tracking, connection pool monitoring, alerts
- ✅ **Health Checks**: Database connectivity, query performance, sync status, resource usage
- ✅ **Backward Compatibility**: 100% compatible with existing code

## Architecture

```
DatabaseAgent (BaseAgent)
├── Query Optimization
│   ├── Slow Query Detection
│   ├── Index Suggestions
│   ├── Query Plan Analysis
│   └── Automatic Index Creation (optional)
├── Sync Management
│   ├── SQLite ↔ Supabase Sync
│   ├── Conflict Resolution
│   ├── Sync Status Tracking
│   └── Sync Metrics
├── Performance Monitoring
│   ├── Query Performance Tracking
│   ├── Database Health Monitoring
│   ├── Connection Pool Monitoring
│   └── Performance Alerts
└── Health Checks
    ├── Database Connectivity
    ├── Query Performance
    ├── Sync Status
    └── Resource Usage
```

## Installation

The Database Agent is part of the BEYONDLINES codebase. No additional installation is required.

## Configuration

Configuration is managed via `src/agents/config/database_agent.yaml`. Key settings include:

### Query Optimization

```yaml
query_optimization:
  enabled: true
  slow_query_threshold_ms: 100.0
  auto_suggest_indexes: true
  auto_create_indexes: false  # Safety: require manual approval
```

### Sync Management

```yaml
sync_management:
  enabled: true
  default_sync_limit: 100
  conflict_resolution_strategy: "supabase_source_of_truth"
```

### Performance Monitoring

```yaml
performance_monitoring:
  enabled: true
  thresholds:
    query_latency_p95_ms: 100.0
    sync_latency_ms: 1000.0
```

## Usage

### Basic Usage

```python
from src.database.database_agent import DatabaseAgent

# Create agent instance
agent = DatabaseAgent(
    agent_id="database_agent",
    agent_name="Database Agent",
    agent_version="2.0.0"
)

# Initialize
await agent.initialize()

# Execute a task
result = await agent.execute({
    "task_type": "save_post",
    "data": {
        "post_id": "test_123",
        "platform": "twitter",
        "content": "Test content"
    }
})

# Health check
health = await agent.health_check()

# Shutdown
await agent.shutdown()
```

### Query Optimization

```python
# Optimize queries
result = await agent.execute({
    "task_type": "optimize_queries",
    "data": {}
})

# Get slow queries
slow_queries = await agent.identify_slow_queries(threshold_ms=100.0)

# Get index suggestions
suggestions = await agent.suggest_indexes()

# Analyze query plan
plan = await agent.analyze_query_plan("SELECT * FROM posts WHERE platform = 'twitter'")
```

### Sync Management

```python
# Sync databases
result = await agent.execute({
    "task_type": "sync_databases",
    "limit": 100
})

# Resolve conflicts
conflicts = await agent.resolve_sync_conflicts()

# Get sync metrics
metrics = agent.get_sync_metrics()
```

### Performance Monitoring

```python
# Analyze performance
result = await agent.execute({
    "task_type": "analyze_performance",
    "data": {}
})

# Track query performance
agent.track_query_performance("query_hash", latency_seconds=0.1)
```

### Health Checks

```python
# Comprehensive health check
health = await agent.health_check()

# Check specific components
connectivity = await agent._test_connectivity()
```

## Task Types

The agent supports the following task types:

| Task Type | Description | Required Data |
|-----------|-------------|---------------|
| `save_post` | Save a post to the database | `data`: Post dictionary |
| `optimize_queries` | Run query optimization | `data`: Optional parameters |
| `sync_databases` | Sync SQLite and Supabase | `limit`: Max records to sync |
| `health_check` | Perform health check | None |
| `analyze_performance` | Analyze database performance | None |
| `suggest_indexes` | Get index suggestions | None |

## Events

The agent publishes the following events:

- `agent.initialized`: Agent initialization complete
- `agent.task_completed`: Task execution complete
- `agent.task_failed`: Task execution failed
- `agent.status_change`: Agent status changed
- `agent.shutdown`: Agent shutdown
- `database.sync_completed`: Database sync completed
- `database.performance_alert`: Performance alert triggered

## Metrics

The agent tracks the following metrics:

### Base Metrics (from BaseAgent)

- `tasks_completed`: Number of completed tasks
- `tasks_failed`: Number of failed tasks
- `tasks_total`: Total number of tasks
- `execution_time_avg`: Average execution time
- `execution_time_total`: Total execution time
- `uptime_seconds`: Agent uptime

### Database-Specific Metrics

- `query_optimization_runs`: Number of optimization runs
- `slow_queries_identified`: Number of slow queries found
- `index_suggestions_generated`: Number of index suggestions
- `sync_operations`: Number of sync operations
- `sync_latency`: Sync operation latency
- `sync_success_rate`: Sync success rate
- `conflicts_resolved`: Number of conflicts resolved
- `performance_analysis_runs`: Number of performance analyses

## Health Check

The health check returns comprehensive information:

```python
{
    "agent_id": "database_agent",
    "agent_name": "Database Agent",
    "status": "idle",
    "healthy": true,
    "database_connectivity": {
        "supabase": true,
        "sqlite": true,
        "overall": true
    },
    "query_performance": {
        "p95_latency_ms": 85.0,
        "avg_latency_ms": 45.0,
        "query_count": 1000,
        "healthy": true
    },
    "sync_status": {
        "synced_percentage": 98.5,
        "unsynced_count": 15,
        "healthy": true
    },
    "resource_usage": {
        "query_cache_size": 50,
        "performance_tracking_size": 5000,
        "status": "normal"
    }
}
```

## Error Handling

The agent handles errors gracefully:

- **Initialization failures**: Agent enters ERROR state, error logged
- **Task execution failures**: Task marked as failed, metrics updated, event published
- **Sync failures**: Sync marked as failed, metrics updated, error returned
- **Query optimization failures**: Error logged, partial results returned

## Performance

### Benchmarks

- **Query latency (p95)**: < 100ms
- **Sync latency**: < 1 second
- **Health check latency**: < 200ms
- **Initialization time**: < 5 seconds

### Optimization Tips

1. **Query Performance**: Use indexes suggested by the agent
2. **Sync Performance**: Adjust `sync_limit` based on data volume
3. **Health Checks**: Disable frequent health checks in production if not needed
4. **Metrics**: Adjust metrics retention based on storage constraints

## Testing

### Unit Tests

```bash
pytest tests/agents/test_database_agent.py -v
```

### Integration Tests

```bash
pytest tests/agents/integration/test_database_flow.py -v
```

### Coverage

Target: 95%+ coverage

```bash
pytest tests/agents/test_database_agent.py --cov=src.database.database_agent --cov-report=html
```

## Troubleshooting

### Common Issues

1. **Initialization fails**: Check database connectivity
2. **Slow queries**: Review index suggestions
3. **Sync failures**: Check network connectivity and database status
4. **Performance alerts**: Review query patterns and indexes

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("src.database.database_agent").setLevel(logging.DEBUG)
```

## Migration Guide

### From v1.0 to v2.0

The agent maintains 100% backward compatibility. No code changes required.

### New Features

To use new features:

```python
# Old way (still works)
agent = DatabaseAgent()
agent.save_post(post)

# New way (with BaseAgent features)
agent = DatabaseAgent()
await agent.initialize()
result = await agent.execute({"task_type": "save_post", "data": post})
```

## API Reference

See [API Reference](./DATABASE_AGENT_API.md) for complete API documentation.

## Related Documentation

- [Query Optimization Guide](./QUERY_OPTIMIZATION.md)
- [BaseAgent Documentation](../agents/BASE_AGENT.md)
- [Sync Management Guide](../database/SYNC_MANAGEMENT.md)

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review the API reference
3. Open an issue on GitHub

## Changelog

### v2.0.0 (2025-01-23)

- ✅ Added BaseAgent integration
- ✅ Added query optimization features
- ✅ Enhanced sync management
- ✅ Added performance monitoring
- ✅ Added comprehensive health checks
- ✅ Maintained 100% backward compatibility

### v1.0.0

- Initial release with basic database operations



