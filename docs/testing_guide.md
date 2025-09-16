# Testing Guide

This document outlines the testing strategy and guidelines for the PrisMind project.

## Test Organization

Tests are organized as follows:

```
tests/
├── unit/                 # Unit tests
├── integration/          # Integration tests
├── e2e/                  # End-to-end tests
└── fixtures/             # Test fixtures and data
```

## Test Types

### 1. Unit Tests
- Test individual functions/methods in isolation
- Should be fast and deterministic
- Use mocks for external dependencies
- Naming: `test_<function_name>.py`

### 2. Integration Tests
- Test interactions between components
- May include database or external service interactions
- Use test doubles for external services
- Naming: `test_<feature>_integration.py`

### 3. End-to-End Tests
- Test complete user flows
- Run against a test environment
- May include UI testing
- Naming: `test_<feature>_e2e.py`

## Writing Tests

### Test Structure

```python
def test_functionality_description():
    # Arrange
    # Set up test data and mocks
    
    # Act
    # Call the function being tested
    
    # Assert
    # Verify the expected behavior
```

### Fixtures

Use pytest fixtures for common test setup:

```python
import pytest

@pytest.fixture
def test_user():
    return User(id=1, name="Test User")

def test_user_creation(test_user):
    assert test_user.name == "Test User"
```

### Mocks

Use `unittest.mock` to isolate tests:

```python
from unittest.mock import patch

def test_external_service():
    with patch('module.external_service') as mock_service:
        mock_service.return_value = "mocked response"
        # Test code that uses the external service
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Type
```bash
# Unit tests only
pytest tests/unit

# Integration tests
pytest -m integration

# E2E tests
pytest -m e2e
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=term-missing
```

### Run with Verbose Output
```bash
pytest -v
```

## Test Coverage

We aim for at least 80% test coverage. To check coverage:

```bash
pytest --cov=src --cov-report=html
```

This will generate an HTML report in the `htmlcov` directory.

## Best Practices

1. **Test Naming**: Be descriptive about what's being tested
2. **One Assert Per Test**: Each test should verify one behavior
3. **Use Fixtures**: For common test setup
4. **Isolate Tests**: Tests should not depend on each other
5. **Clean Up**: Ensure tests clean up after themselves
6. **Avoid Flakiness**: Tests should be deterministic
7. **Test Edge Cases**: Include boundary conditions and error cases
8. **Documentation**: Add docstrings to explain test purpose

## Performance Testing

For performance-critical code, use `pytest-benchmark`:

```python
def test_performance(benchmark):
    result = benchmark(my_function)
    assert result == expected_value
```

## Continuous Integration

Tests are automatically run on every push and pull request via GitHub Actions. The CI pipeline includes:
- Unit tests
- Integration tests
- Code coverage reporting
- Code quality checks

## Debugging Tests

To debug a failing test:

1. Run the specific test with `-s` to see print statements:
   ```bash
   pytest tests/path/to/test.py -v -s
   ```

2. Use `pdb` for interactive debugging:
   ```python
   import pdb; pdb.set_trace()
   ```

3. Check the test logs in the CI/CD pipeline for failures.

## Writing Maintainable Tests

- **Readability**: Tests should be easy to understand
- **Independence**: Tests should not depend on each other
- **Speed**: Keep tests fast to enable frequent runs
- **Determinism**: Tests should produce the same results every time
- **Documentation**: Add comments for complex test logic
