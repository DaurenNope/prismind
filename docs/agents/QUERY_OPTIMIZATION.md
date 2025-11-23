# Query Optimization Guide

**Version**: 2.0.0  
**Last Updated**: 2025-01-23

## Overview

The Database Agent includes comprehensive query optimization features to identify slow queries, suggest indexes, analyze query plans, and improve overall database performance.

## Features

- ✅ **Slow Query Detection**: Automatically identify queries exceeding performance thresholds
- ✅ **Index Suggestions**: Generate intelligent index recommendations based on query patterns
- ✅ **Query Plan Analysis**: Analyze query execution plans (where supported)
- ✅ **Automatic Index Creation**: Optional automatic index creation (disabled by default for safety)

## Slow Query Detection

### How It Works

The agent tracks query performance and identifies queries that exceed the configured threshold (default: 100ms for p95 latency).

### Configuration

```yaml
query_optimization:
  slow_query_threshold_ms: 100.0
  track_query_performance: true
  max_tracked_queries_per_hash: 1000
```

### Usage

```python
from src.database.database_agent import DatabaseAgent

agent = DatabaseAgent()
await agent.initialize()

# Identify slow queries
slow_queries = await agent.identify_slow_queries(threshold_ms=100.0)

# Results include:
# - query_hash: Hash of the query
# - avg_latency_ms: Average latency in milliseconds
# - max_latency_ms: Maximum latency in milliseconds
# - p95_latency_ms: 95th percentile latency in milliseconds
# - execution_count: Number of times the query was executed
```

### Example Output

```python
[
    {
        "query_hash": "abc123",
        "avg_latency_ms": 150.5,
        "max_latency_ms": 250.0,
        "p95_latency_ms": 200.0,
        "execution_count": 100,
        "threshold_ms": 100.0
    }
]
```

## Index Suggestions

### How It Works

The agent analyzes slow queries and query patterns to suggest indexes that would improve performance.

### Usage

```python
# Get index suggestions
result = await agent.suggest_indexes()

# Results include:
# - suggestions: List of index suggestions
# - count: Number of suggestions
```

### Example Output

```python
{
    "suggestions": [
        {
            "table": "posts",
            "columns": ["platform"],
            "type": "btree",
            "reason": "Frequent filtering by platform",
            "estimated_improvement": "High"
        },
        {
            "table": "posts",
            "columns": ["platform", "created_at"],
            "type": "btree",
            "reason": "Composite index for platform + created_at queries",
            "estimated_improvement": "Very High"
        }
    ],
    "count": 2
}
```

### Index Types

- **btree**: Standard B-tree index (most common)
- **gin**: Generalized Inverted Index (for arrays, JSONB)
- **gist**: Generalized Search Tree (for geometric data, full-text search)

### When to Create Indexes

1. **High Frequency Queries**: Queries executed frequently (> 100 times/day)
2. **Slow Queries**: Queries with p95 latency > threshold
3. **Filtered Columns**: Columns used frequently in WHERE clauses
4. **Ordered Columns**: Columns used frequently in ORDER BY clauses
5. **Join Columns**: Columns used in JOIN conditions

### Index Creation

#### Automatic (Optional)

```yaml
query_optimization:
  auto_create_indexes: true  # WARNING: Use with caution
```

#### Manual (Recommended)

```python
# Get suggestions
suggestions = await agent.suggest_indexes()

# Review suggestions
for suggestion in suggestions["suggestions"]:
    print(f"CREATE INDEX ON {suggestion['table']} ({', '.join(suggestion['columns'])})")

# Create via migration
# See migrations/ directory for examples
```

## Query Plan Analysis

### How It Works

The agent analyzes query execution plans to understand how queries are executed and identify optimization opportunities.

### Usage

```python
# Analyze query plan
plan = await agent.analyze_query_plan(
    "SELECT * FROM posts WHERE platform = 'twitter' ORDER BY created_at DESC LIMIT 100"
)

# Results include:
# - query: The analyzed query
# - estimated_cost: Estimated query cost
# - analysis: Analysis of the query plan
# - recommendations: Optimization recommendations
```

### Example Output

```python
{
    "query": "SELECT * FROM posts WHERE platform = 'twitter'...",
    "estimated_cost": "N/A",
    "analysis": "Query plan analysis requires direct database access",
    "recommendations": []
}
```

**Note**: Full query plan analysis requires direct database access (via RPC or direct SQL). The current implementation provides a framework for future enhancement.

## Full Query Optimization Workflow

### Step-by-Step Process

1. **Track Query Performance**

```python
# The agent automatically tracks query performance
# You can also manually track:
agent.track_query_performance("query_hash", latency_seconds=0.1)
```

2. **Identify Slow Queries**

```python
slow_queries = await agent.identify_slow_queries(threshold_ms=100.0)
```

3. **Get Index Suggestions**

```python
suggestions = await agent.suggest_indexes()
```

4. **Analyze Query Plans**

```python
for query_info in slow_queries:
    query_hash = query_info["query_hash"]
    # Get actual query from your application
    plan = await agent.analyze_query_plan(actual_query)
```

5. **Apply Optimizations**

```python
# Review suggestions and create indexes via migration
# Or use automatic creation (if enabled)
```

6. **Monitor Results**

```python
# Re-run optimization to see improvements
result = await agent.optimize_queries()
```

### Complete Example

```python
from src.database.database_agent import DatabaseAgent

async def optimize_database():
    # Initialize agent
    agent = DatabaseAgent()
    await agent.initialize()
    
    # Run full optimization
    result = await agent.execute({
        "task_type": "optimize_queries",
        "data": {}
    })
    
    # Review results
    print(f"Slow queries found: {len(result['slow_queries'])}")
    print(f"Index suggestions: {len(result['index_suggestions'])}")
    
    # Apply index suggestions
    for suggestion in result['index_suggestions']:
        print(f"Suggested index: {suggestion['table']} ({', '.join(suggestion['columns'])})")
        # Create index via migration or manual SQL
    
    return result
```

## Best Practices

### 1. Regular Optimization

Run query optimization regularly (e.g., weekly):

```python
# Schedule optimization task
result = await agent.execute({
    "task_type": "optimize_queries",
    "data": {}
})
```

### 2. Review Suggestions

Always review index suggestions before creating:

- Check query frequency
- Verify column usage patterns
- Consider index maintenance overhead
- Test in staging environment first

### 3. Monitor Performance

Track performance after applying optimizations:

```python
# Before optimization
before = await agent.analyze_performance()

# Apply optimizations
# ... create indexes ...

# After optimization
after = await agent.analyze_performance()

# Compare results
improvement = before["query_performance"]["p95_latency_ms"] - after["query_performance"]["p95_latency_ms"]
print(f"Improvement: {improvement}ms")
```

### 4. Index Maintenance

- **Monitor index usage**: Remove unused indexes
- **Rebuild indexes**: Periodically rebuild indexes (PostgreSQL: `REINDEX`)
- **Update statistics**: Keep query planner statistics up to date (`ANALYZE`)

### 5. Composite Indexes

Consider composite indexes for multi-column queries:

```python
# Single column indexes
idx_platform ON posts(platform)
idx_created_at ON posts(created_at)

# Composite index (better for queries filtering both)
idx_platform_created_at ON posts(platform, created_at)
```

## Common Patterns

### Pattern 1: Platform Filtering

**Query**:
```sql
SELECT * FROM posts WHERE platform = 'twitter' ORDER BY created_at DESC LIMIT 100
```

**Suggestion**:
```sql
CREATE INDEX idx_posts_platform_created_at ON posts(platform, created_at DESC);
```

### Pattern 2: Date Range Queries

**Query**:
```sql
SELECT * FROM posts WHERE created_at > '2025-01-01' AND platform = 'reddit'
```

**Suggestion**:
```sql
CREATE INDEX idx_posts_platform_created_at ON posts(platform, created_at);
```

### Pattern 3: Full-Text Search

**Query**:
```sql
SELECT * FROM posts WHERE content LIKE '%keyword%'
```

**Suggestion**:
```sql
-- For PostgreSQL
CREATE INDEX idx_posts_content_gin ON posts USING gin(to_tsvector('english', content));
```

## Troubleshooting

### Issue: No Slow Queries Detected

**Possible Causes**:
- Queries are actually fast
- Not enough query data tracked
- Threshold too high

**Solutions**:
- Lower threshold: `identify_slow_queries(threshold_ms=50.0)`
- Track more queries
- Review query patterns manually

### Issue: Too Many Index Suggestions

**Possible Causes**:
- Many slow queries
- Queries not optimized

**Solutions**:
- Review and prioritize suggestions
- Focus on high-frequency queries first
- Consider composite indexes

### Issue: Index Creation Fails

**Possible Causes**:
- Insufficient permissions
- Index already exists
- Invalid column names

**Solutions**:
- Check database permissions
- Verify index doesn't exist: `SELECT * FROM pg_indexes WHERE indexname = 'index_name'`
- Validate column names

## Performance Impact

### Index Creation

- **Time**: Varies by table size (seconds to minutes)
- **Lock**: May lock table during creation (use `CONCURRENTLY` in PostgreSQL)
- **Storage**: Each index uses additional storage space

### Query Performance

- **Improvement**: 10x to 1000x faster queries (depending on query)
- **Maintenance**: Minimal overhead for INSERT/UPDATE/DELETE operations

## Advanced Topics

### Custom Query Tracking

```python
import time
import hashlib

# Track custom query
query = "SELECT * FROM posts WHERE platform = 'twitter'"
query_hash = hashlib.md5(query.encode()).hexdigest()

start = time.time()
# Execute query
result = execute_query(query)
latency = time.time() - start

# Track performance
agent.track_query_performance(query_hash, latency)
```

### Query Plan Caching

The agent caches query plans to avoid repeated analysis:

```python
# Plans are automatically cached
plan = await agent.analyze_query_plan(query)  # First call: analyzes
plan = await agent.analyze_query_plan(query)  # Second call: uses cache
```

## Related Documentation

- [Database Agent Documentation](./DATABASE_AGENT.md)
- [PostgreSQL Index Documentation](https://www.postgresql.org/docs/current/indexes.html)
- [Supabase Performance Guide](https://supabase.com/docs/guides/database/performance)

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review query patterns in your application
3. Consult database-specific documentation
4. Open an issue on GitHub



