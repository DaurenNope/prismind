#!/usr/bin/env python3
"""
Example: Using the New Observability and Testing Tools
======================================================

This example demonstrates how to use:
1. Observability Hub - Unified logging, tracing, metrics
2. Configuration Validation - Schema validation
3. Test Infrastructure - Test data factories and mocks
4. Migration System - Database schema management
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.migration_system import get_migration_manager
from src.utils.config_validator import (
    create_beyondlines_config_validator,
    validate_config,
)
from src.utils.observability_hub import get_observability_hub, instrument_function
from src.utils.test_infrastructure import (
    IntegrationTestHelper,
    MockSupabase,
    create_test_post,
    create_test_posts,
)

# Example 1: Using Observability Hub
print("=" * 60)
print("Example 1: Observability Hub")
print("=" * 60)

hub = get_observability_hub()


# Instrument a function automatically
@hub.instrument_function(track_metrics=True, track_errors=True, track_trace=True)
async def example_operation(name: str, value: int):
    """An example operation that gets automatically instrumented"""
    await asyncio.sleep(0.1)  # Simulate work
    if value < 0:
        raise ValueError(f"Value must be positive, got {value}")
    return f"Processed {name} with value {value}"


# Run instrumented function
try:
    result = await example_operation("test", 42)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error (expected): {e}")

# Get health report
health = hub.get_health_report()
print(f"\nHealth Report:")
print(f"  Service: {health['service']}")
print(f"  Metrics: {len(health['metrics']['summary'])} metrics")
print(f"  Errors: {health['errors']['total_errors']} total errors")

# Example 2: Configuration Validation
print("\n" + "=" * 60)
print("Example 2: Configuration Validation")
print("=" * 60)

config = {
    "supabase_url": "https://example.supabase.co",
    "supabase_service_role_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example",
    "supabase_enabled": True,
    "enable_analysis": True,
    "auto_pipeline_batch_limit": 50,
    "rewriter_min_quality_score": 7.5,
}

result = validate_config(config)
if result.is_valid:
    print("✅ Configuration is valid!")
    print(f"Validated config: {list(result.validated_config.keys())}")
else:
    print("❌ Configuration validation failed:")
    for error in result.errors:
        print(f"  - {error}")

# Example 3: Test Infrastructure
print("\n" + "=" * 60)
print("Example 3: Test Infrastructure")
print("=" * 60)

# Create test posts
test_post = create_test_post(platform="twitter", content="Test post content")
print(f"Created test post: {test_post.post_id}")
print(f"  Platform: {test_post.platform}")
print(f"  Content: {test_post.content[:50]}...")

# Create multiple test posts
test_posts = create_test_posts(3, platform="reddit")
print(f"\nCreated {len(test_posts)} test posts")

# Use mock Supabase
mock_supabase = MockSupabase()
query = mock_supabase.table("posts").select("*").eq("platform", "twitter").limit(10)
result = query.execute()
print(f"\nMock Supabase query returned {len(result.data)} posts")

# Example 4: Migration System
print("\n" + "=" * 60)
print("Example 4: Migration System")
print("=" * 60)

migration_manager = get_migration_manager()
status = migration_manager.get_status()
print(f"Migration Status:")
print(f"  Total migrations: {status['total_migrations']}")
print(f"  Applied: {status['applied_count']}")
print(f"  Pending: {status['pending_count']}")
print(f"  Failed: {status['failed_count']}")

if status["pending_count"] > 0:
    print(f"\nPending migrations: {status['pending_versions']}")
else:
    print("\n✅ No pending migrations")

# Example 5: Integration Test Helper
print("\n" + "=" * 60)
print("Example 5: Integration Test Helper")
print("=" * 60)

helper = IntegrationTestHelper()
mock_db = helper.setup_mock_supabase()

# Seed test data
test_data = [post.to_dict() for post in create_test_posts(5)]
helper.seed_database("posts", test_data)

# Query mock database
posts = mock_db.table("posts").select("*").execute()
print(f"Seeded {len(posts.data)} posts in mock database")

# Cleanup
helper.teardown()
print("✅ Test helper cleaned up")

print("\n" + "=" * 60)
print("All examples completed!")
print("=" * 60)
