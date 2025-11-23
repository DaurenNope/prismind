# New Tools Implementation Guide

This document describes the new observability, testing, configuration, and migration tools added to BEYONDLINES.

## Overview

Four major tooling improvements have been implemented:

1. **Observability Hub** - Unified logging, tracing, metrics, and error tracking
2. **Configuration Validation** - Schema-based config validation with clear error messages
3. **Test Infrastructure** - Test data factories, mocks, and utilities
4. **Migration System** - Database schema version management with rollback support

## 1. Observability Hub

**Location**: `src/utils/observability_hub.py`

### Purpose
Provides unified observability with:
- Structured logging with correlation IDs
- Distributed tracing across services
- Metrics collection (Prometheus-style counters, gauges, histograms)
- Error tracking and aggregation

### Usage

```python
from src.utils.observability_hub import get_observability_hub, instrument_function

# Get the hub
hub = get_observability_hub()

# Option 1: Auto-instrument functions with decorator
@hub.instrument_function(track_metrics=True, track_errors=True, track_trace=True)
async def my_function(name: str, value: int):
    # Function automatically gets:
    # - Logging
    # - Tracing
    # - Metrics (call count, duration, errors)
    # - Error tracking
    return result

# Option 2: Manual metrics
hub.metrics.increment("operations.called", labels={"operation": "process_post"})
hub.metrics.record_histogram("operations.duration", duration_seconds)

# Option 3: Error tracking
try:
    risky_operation()
except Exception as e:
    hub.errors.capture_exception(e, context={"operation": "process_post"})

# Get health report
health = hub.get_health_report()
print(f"Metrics: {len(health['metrics']['summary'])}")
print(f"Errors: {health['errors']['total_errors']}")
```

### Integration

To integrate into existing code, wrap critical functions:

```python
from src.utils.observability_hub import instrument_function

@instrument_function(operation_name="save_post")
def save_post(post):
    # Your existing code
    pass
```

## 2. Configuration Validation

**Location**: `src/utils/config_validator.py`

### Purpose
Validates configuration with:
- Type checking
- Value constraints (min/max, length, patterns)
- Required field validation
- Clear error messages

### Usage

```python
from src.utils.config_validator import validate_config, create_beyondlines_config_validator

# Validate with default BEYONDLINES schema
config = {
    "supabase_url": "https://example.supabase.co",
    "supabase_service_role_key": "key_here",
    "enable_analysis": True
}

result = validate_config(config)
if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")
else:
    validated_config = result.validated_config
    # Use validated config
```

### Custom Validation

```python
from src.utils.config_validator import ConfigValidator, ConfigValueType

validator = ConfigValidator()

# Add fields with validation rules
validator.add_field(
    "database_url",
    ConfigValueType.URL,
    required=True,
    description="Database connection URL"
)

validator.add_field(
    "max_connections",
    ConfigValueType.INTEGER,
    required=False,
    default=10,
    min_value=1,
    max_value=100,
    description="Maximum database connections"
)

# Validate
result = validator.validate(config_dict)
```

## 3. Test Infrastructure

**Location**: `src/utils/test_infrastructure.py`

### Purpose
Provides utilities for testing:
- Test data factories (create test posts, analyzed posts, etc.)
- Mock Supabase client for testing
- Integration test helpers
- Test database utilities

### Usage

```python
from src.utils.test_infrastructure import (
    create_test_post,
    create_test_posts,
    MockSupabase,
    IntegrationTestHelper
)

# Create test posts
post = create_test_post(platform="twitter", content="Test content")
posts = create_test_posts(5, platform="reddit")

# Use mock Supabase
mock_supabase = MockSupabase()
mock_supabase.table("posts").insert(post.to_dict()).execute()

# Integration test helper
helper = IntegrationTestHelper()
mock_db = helper.setup_mock_supabase()

# Seed test data
helper.seed_database("posts", [post.to_dict() for post in create_test_posts(10)])

# Run tests
# ...

# Cleanup
helper.teardown()
```

### Example Test

```python
import pytest
from src.utils.test_infrastructure import IntegrationTestHelper, create_test_post

@pytest.fixture
def test_helper():
    helper = IntegrationTestHelper()
    helper.setup_mock_supabase()
    yield helper
    helper.teardown()

async def test_post_analysis(test_helper):
    # Create test post
    post = create_test_post(platform="twitter")

    # Run analysis
    result = await analyze_post(post.to_dict())

    # Assertions
    assert result['ai_summary'] is not None
    assert result['value_score'] > 0
```

## 4. Migration System

**Location**: `src/database/migration_system.py`

### Purpose
Manages database schema migrations with:
- Version tracking
- Up/down migrations
- Rollback support
- Migration history

### Usage

```python
from src.database.migration_system import get_migration_manager

# Get migration manager
manager = get_migration_manager(supabase_client=supabase_client)

# Create a new migration
migration = manager.create_migration(
    name="add_user_table",
    up_sql="""
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    down_sql="""
    DROP TABLE users;
    """
)

# Apply pending migrations
applied_count, errors = manager.apply_migrations()
print(f"Applied {applied_count} migrations")

# Rollback a migration
success = manager.rollback(version="20250101_001234")
if success:
    print("Migration rolled back successfully")

# Check status
status = manager.get_status()
print(f"Pending: {status['pending_count']}")
print(f"Applied: {status['applied_count']}")
```

### Migration File Format

Migration files should be named: `YYYYMMDD_HHMMSS_description.sql`

Example: `20250116_143022_add_rewrite_scores.sql`

```sql
-- Add rewrite scores to posts table

-- UP
ALTER TABLE posts
ADD COLUMN rewrite_score FLOAT DEFAULT 0.0,
ADD COLUMN rewrite_readiness VARCHAR(50);

-- DOWN
ALTER TABLE posts
DROP COLUMN rewrite_score,
DROP COLUMN rewrite_readiness;
```

## Integration Examples

### Example 1: Instrument DatabaseAgent

```python
from src.database.database_agent import DatabaseAgent
from src.utils.observability_hub import instrument_function

class DatabaseAgent:
    @instrument_function(operation_name="save_post")
    def save_post(self, post):
        # Existing implementation
        pass
```

### Example 2: Validate Configuration on Startup

```python
from src.utils.config_validator import validate_config
from src.utils.config import get_config

def startup():
    config = get_config().__dict__
    result = validate_config(config)

    if not result.is_valid:
        raise RuntimeError(f"Configuration invalid: {result.errors}")

    # Use validated config
    return result.validated_config
```

### Example 3: Full Integration Test

```python
from src.utils.test_infrastructure import IntegrationTestHelper, create_test_post
from src.services.analysis.post_analyzer import analyze_and_store_post

async def test_analysis_pipeline():
    helper = IntegrationTestHelper()
    mock_db = helper.setup_mock_supabase()

    # Create test post
    post = create_test_post(platform="twitter")

    # Run analysis
    result = await analyze_and_store_post(
        mock_db,
        post.to_dict(),
        supabase_manager=None
    )

    # Verify
    assert result is True
    stored_posts = mock_db.table("posts").select("*").execute()
    assert len(stored_posts.data) == 1

    helper.teardown()
```

## Next Steps

### Recommended Integrations

1. **Add observability to critical paths:**
   - `DatabaseAgent.save_post()`
   - `Orchestrator.analyze_batch()`
   - `PostAnalyzer.analyze_and_store_post()`

2. **Validate configuration on startup:**
   - Add validation to `main.py` startup
   - Validate environment variables
   - Validate JSON config files

3. **Add test utilities to existing tests:**
   - Replace manual test data creation with factories
   - Use mock Supabase for integration tests
   - Add IntegrationTestHelper for complex tests

4. **Create migrations for schema changes:**
   - Use migration system for all schema changes
   - Document migrations in migration files
   - Test migrations before applying

## Benefits

These tools provide:

1. **Better Observability** - Understand system behavior in production
2. **Configuration Safety** - Catch config errors early
3. **Faster Testing** - Easier to write and maintain tests
4. **Safer Deployments** - Controlled schema changes with rollback

## Files Created

- `src/utils/observability_hub.py` - Observability Hub
- `src/utils/config_validator.py` - Configuration Validation
- `src/utils/test_infrastructure.py` - Test Infrastructure
- `src/database/migration_system.py` - Migration System
- `examples/using_new_tools.py` - Usage examples
- `docs/TOOLS_IMPLEMENTATION.md` - This document
