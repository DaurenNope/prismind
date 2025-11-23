# Testing Guide

## Overview

This guide covers the testing structure, procedures, and best practices for the Prismind codebase.

---

## Test Structure

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_collectors.py       # Collector unit tests
├── test_analyzers.py        # Analyzer unit tests
├── test_database_operations.py  # Database operation tests
├── test_database_consistency.py # Database consistency tests
├── test_transactions.py     # Transaction handling tests
├── test_e2e_workflows.py   # End-to-end workflow tests
├── test_rewriter.py        # Rewriter component tests
├── test_persona_matcher.py # Persona matcher tests
├── test_persona_manager.py # Persona manager tests
├── test_rag_fallback.py   # RAG system tests
├── test_automated_checklist.py # Automated checklist tests
└── README_TESTING.md       # This file
```

### Test Categories

#### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- No external dependencies
- Mock all external services
- Run by default

#### Integration Tests (`@pytest.mark.integration`)
- Test component interactions
- May require test database
- Mock external APIs
- Run with `pytest -m integration`

#### E2E Tests (`@pytest.mark.e2e`)
- Full system tests
- Require full system setup
- May be slow
- Run with `pytest -m e2e`

#### Performance Tests (`@pytest.mark.performance`)
- Performance benchmarks
- Load tests
- Run with `pytest -m performance`

---

## Running Tests

### Run All Unit Tests (Default)
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest -m "not integration and not e2e"

# Integration tests
pytest -m integration

# E2E tests
pytest -m e2e

# Performance tests
pytest -m performance
```

### Run Specific Test Files
```bash
# Single file
pytest tests/test_collectors.py

# Multiple files
pytest tests/test_collectors.py tests/test_analyzers.py
```

### Run Specific Tests
```bash
# By name
pytest tests/test_collectors.py::TestTwitterCollector::test_collect_twitter_bookmarks_basic

# By pattern
pytest -k "test_collect"
```

### Run with Coverage
```bash
# Full coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html

# Coverage threshold
pytest --cov=src --cov-fail-under=80
```

---

## Test Data

### Fixtures

Common fixtures are defined in `conftest.py`:

#### Post Fixtures
- `sample_post` - Standard test post
- `sample_truncated_post` - Truncated post
- `sample_error_post` - Error post
- `sample_analyzed_content` - Analyzed content

#### Persona Fixtures
- `sample_persona_config` - Sample persona config
- `qronoya_persona_config` - Qronoya persona

#### Mock Fixtures
- `mock_database` - Mock database manager
- `mock_supabase_client` - Mock Supabase client
- `mock_storage_facade` - Mock storage facade
- `mock_rag_system` - Mock RAG system
- `mock_ai_service` - Mock AI service

#### Generator Fixtures
- `generate_test_posts()` - Generate test posts
- `generate_test_personas()` - Generate test personas
- `generate_test_rewrite_angles()` - Generate rewrite angles

### Using Fixtures

```python
def test_example(sample_post, mock_database):
    """Test using fixtures"""
    # Use sample_post and mock_database
    assert sample_post['post_id'] == 'test_post_123'
```

---

## Test Procedures

### Writing New Tests

1. **Choose Test Category**
   - Unit test: Fast, isolated
   - Integration test: Component interaction
   - E2E test: Full system

2. **Use Appropriate Fixtures**
   - Use existing fixtures when possible
   - Create new fixtures if needed

3. **Mock External Dependencies**
   - Mock database calls
   - Mock API calls
   - Mock file system operations

4. **Test Edge Cases**
   - Empty inputs
   - None values
   - Error conditions
   - Boundary conditions

5. **Assert Clearly**
   - Use descriptive assertions
   - Test one thing per test
   - Use meaningful test names

### Example Test

```python
@pytest.mark.unit
class TestMyComponent:
    """Test my component"""
    
    @pytest.fixture
    def my_component(self):
        """Create component instance"""
        return MyComponent()
    
    def test_basic_functionality(self, my_component):
        """Test basic functionality"""
        result = my_component.do_something()
        assert result is not None
        assert result.status == 'success'
    
    def test_error_handling(self, my_component):
        """Test error handling"""
        with pytest.raises(ValueError):
            my_component.do_something(invalid_input=True)
```

---

## Test Quality Guidelines

### Maintainability
- **Clear test names**: Describe what is being tested
- **Single responsibility**: One test, one assertion
- **DRY principle**: Use fixtures and helpers
- **Documentation**: Add docstrings for complex tests

### Speed
- **Fast unit tests**: < 100ms per test
- **Mock external calls**: Don't make real API calls
- **Use fixtures**: Avoid setup/teardown overhead
- **Parallel execution**: Tests should be independent

### Reliability
- **Deterministic**: Tests should always pass or fail consistently
- **No flaky tests**: Don't rely on timing or external state
- **Clean state**: Each test should start fresh
- **Error handling**: Test error conditions

---

## CI/CD Integration

### Test Execution in CI

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests

### CI Jobs

1. **Unit Tests**: Fast tests, run on every commit
2. **Integration Tests**: May require test database
3. **E2E Tests**: Full system tests
4. **Coverage Report**: Generated and uploaded
5. **Performance Tests**: Benchmarks and load tests

### Coverage Requirements

- **Target**: 80%+ coverage
- **Critical paths**: 90%+ coverage
- **CI enforcement**: Fails if coverage drops below threshold

---

## Troubleshooting

### Tests Failing Locally

1. **Check Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Check Environment**
   ```bash
   export TESTING=true
   ```

3. **Run with Verbose Output**
   ```bash
   pytest -v --tb=short
   ```

### Integration Tests Failing

1. **Check Test Database**
   - Ensure test database is configured
   - Check credentials in environment

2. **Check External Services**
   - Some tests require mocked services
   - Check test setup

### Coverage Issues

1. **Check Coverage Report**
   ```bash
   pytest --cov=src --cov-report=html
   open htmlcov/index.html
   ```

2. **Identify Gaps**
   - Review uncovered lines
   - Add tests for critical paths

---

## Best Practices

1. **Test First**: Write tests before or alongside code
2. **Test Behavior**: Test what code does, not how
3. **Test Edge Cases**: Don't just test happy paths
4. **Keep Tests Fast**: Mock slow operations
5. **Keep Tests Simple**: Complex tests are hard to maintain
6. **Use Fixtures**: Share test data and setup
7. **Document Tests**: Explain complex test logic
8. **Review Tests**: Tests are code too, review them

---

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python.org/3/library/unittest.html)

---

**Last Updated**: Generated with test infrastructure
**Maintainer**: Testing & QA Team






