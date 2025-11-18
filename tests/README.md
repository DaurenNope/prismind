# Prismind Test Suite

## Overview

This directory contains comprehensive tests for the Prismind project, including unit tests, integration tests, and end-to-end tests.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── test_orchestrator_error_handling.py  # Unit tests for orchestrator error handling
├── test_database_agent_curation.py      # Unit tests for automatic curation
├── test_integration_analysis_pipeline.py # Integration tests for analysis pipeline
└── README.md                      # This file
```

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_orchestrator_error_handling.py
```

### Run specific test
```bash
pytest tests/test_orchestrator_error_handling.py::TestOrchestratorErrorHandling::test_analyze_batch_logs_errors
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

## Test Categories

### Unit Tests
- **test_orchestrator_error_handling.py**: Tests error handling and logging in the orchestrator
- **test_database_agent_curation.py**: Tests automatic curation to usable_posts table

### Integration Tests
- **test_integration_analysis_pipeline.py**: Tests the full analysis pipeline flow

## Test Fixtures

Common fixtures are defined in `conftest.py`:
- `sample_post`: A valid sample post for testing
- `sample_truncated_post`: A truncated post for testing
- `sample_error_post`: An error post for testing

## Writing New Tests

1. Create a new test file following the naming convention `test_*.py`
2. Import necessary fixtures from `conftest.py`
3. Use `@pytest.mark.asyncio` for async tests
4. Use `@pytest.fixture` for test fixtures
5. Follow the existing test structure and patterns

## Test Coverage Goals

- **Unit Tests**: 80%+ coverage for core components
- **Integration Tests**: Cover all major workflows
- **Error Handling**: Test all error paths
- **Edge Cases**: Test boundary conditions

## Continuous Integration

Tests are automatically run in CI/CD pipeline:
- On every push to main branch
- On pull requests
- Before deployment

## Debugging Tests

### Run tests with debug output
```bash
pytest tests/ -v -s
```

### Run tests with pdb on failure
```bash
pytest tests/ --pdb
```

### Run tests with logging
```bash
pytest tests/ --log-cli-level=DEBUG
```

## Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Mocking**: Use mocks for external dependencies (APIs, databases)
3. **Fixtures**: Use fixtures for common test data
4. **Assertions**: Use descriptive assertion messages
5. **Cleanup**: Clean up after tests (use fixtures with teardown)

## Known Issues

- Some integration tests require database access and may be skipped in CI
- Some tests may require specific environment variables to be set

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve test coverage
4. Update this README if needed
