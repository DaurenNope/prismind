# Integration Tests

Comprehensive integration tests for critical workflows in the Prismind system.

## Overview

This test suite provides end-to-end integration tests for:

1. **Collection → Analysis → Database E2E** - Complete workflow from collection to storage
2. **Research Agents** - Research agent integration and workflows
3. **GitHub Integration** - GitHub trending and repository metadata
4. **Quality Pipeline** - Quality filtering, ranking, and scoring
5. **Platform Collection** - Platform-specific collection workflows
6. **Performance Benchmarks** - Performance testing for critical operations

## Test Structure

```
tests/integration/
├── __init__.py
├── conftest.py                    # Test configuration and fixtures
├── test_collection_analysis_db_e2e.py
├── test_research_agents.py
├── test_github_integration.py
├── test_quality_pipeline.py
├── test_platform_collection.py
├── test_performance_benchmarks.py
├── fixtures/
│   └── __init__.py
└── README.md                      # This file
```

## Running Tests

### Run All Integration Tests

```bash
pytest tests/integration/ -v
```

### Run Specific Test Suite

```bash
# E2E tests
pytest tests/integration/test_collection_analysis_db_e2e.py -v

# Research agents
pytest tests/integration/test_research_agents.py -v

# GitHub integration
pytest tests/integration/test_github_integration.py -v

# Quality pipeline
pytest tests/integration/test_quality_pipeline.py -v

# Platform collection
pytest tests/integration/test_platform_collection.py -v

# Performance benchmarks
pytest tests/integration/test_performance_benchmarks.py -v -m performance
```

### Run with Coverage

```bash
pytest tests/integration/ --cov=src --cov-report=html --cov-report=term-missing
```

### Run Performance Tests Only

```bash
pytest tests/integration/ -m performance -v
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.integration` - Integration tests (default)
- `@pytest.mark.performance` - Performance benchmark tests
- `@pytest.mark.asyncio` - Async tests

## Test Patterns

### Pattern 1: E2E Workflow Test

```python
@pytest.mark.asyncio
async def test_complete_workflow():
    # 1. Setup mocks
    # 2. Execute workflow steps
    # 3. Verify results
    # 4. Check data consistency
```

### Pattern 2: Error Recovery Test

```python
@pytest.mark.asyncio
async def test_error_recovery():
    # 1. Simulate error
    # 2. Verify graceful handling
    # 3. Verify system recovers
    # 4. Verify data integrity
```

### Pattern 3: Performance Benchmark

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_performance():
    # 1. Measure operation time
    # 2. Calculate metrics
    # 3. Compare against baseline
    # 4. Fail if below threshold
```

## Mocking Strategy

All external services are mocked to ensure:
- Tests are deterministic
- No external dependencies required
- Fast test execution
- Isolated test environment

### Mocked Services

- **AI Services** - Ollama, Gemini, Mistral
- **Database** - SQLite, Supabase
- **Platform APIs** - Twitter, Reddit, Threads, Telegram
- **GitHub API** - Repository metadata, trending

## Performance Baselines

### Collection Throughput
- **Target**: > 10 posts/sec
- **Test**: `test_collection_throughput`

### Analysis Latency
- **Target**: < 5 sec/post
- **Test**: `test_analysis_latency`

### Database Write Performance
- **Target**: < 100ms/post
- **Test**: `test_database_write_performance`

### E2E Pipeline Latency
- **Target**: < 30 sec for 10 posts
- **Test**: `test_e2e_pipeline_latency`

## CI/CD Integration

Tests are configured to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Integration Tests
  run: |
    pytest tests/integration/ -v --cov=src --cov-report=xml
```

## Test Coverage Goals

- **Integration Test Coverage**: 80%+ for critical workflows
- **Critical Workflow Coverage**: 100%
- **Error Scenario Coverage**: 70%+

## Troubleshooting

### Tests Failing Due to Missing Mocks

Ensure all external services are properly mocked. Check `conftest.py` for available fixtures.

### Performance Tests Failing

Performance tests use mocked services, so they should be fast. If they're slow, check for:
- Unmocked external calls
- Blocking operations
- Large test datasets

### Async Test Issues

Ensure `@pytest.mark.asyncio` is used for async tests and `pytest-asyncio` is installed.

## Contributing

When adding new integration tests:

1. Use appropriate test markers
2. Mock all external services
3. Include both happy path and error scenarios
4. Document test purpose and expected behavior
5. Add performance benchmarks for critical operations

## Related Documentation

- [Ticket #13.1: Integration Test Coverage](../docs/TICKET_13_1_INTEGRATION_TEST_COVERAGE.md)
- [Unit Tests](../README.md)
- [Testing Checklist](../TESTING_CHECKLIST.md)






