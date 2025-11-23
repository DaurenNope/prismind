# Testing Guide

This directory contains the test suite for BEYONDLINES.

## Test Structure

- **Unit Tests**: Fast, isolated tests for individual components (default)
- **Integration Tests**: Tests for component integration and workflows (`-m integration`)
- **E2E Tests**: End-to-end tests requiring full system (`-m e2e`)
- **Performance Tests**: Performance benchmarks (`-m performance`)
- **System Validation**: Comprehensive system validation (`scripts/validation/system_validation.py`)

## Test Categories

### Integration Tests

| Test File | Purpose | Status |
|-----------|---------|--------|
| `test_integration_collection.py` | Collection → Database flow | ✅ |
| `test_integration_analysis.py` | Analysis → Database flow | ✅ |
| `test_integration_publishing.py` | Publishing workflow | ✅ |
| `test_integration_api.py` | API endpoints | ✅ |
| `test_integration_analysis_pipeline.py` | Full analysis pipeline | ✅ |
| `test_integration.py` | Component integration | ✅ |

## Running Tests

### Run all unit tests (default)
```bash
pytest
```

### Run only unit tests
```bash
pytest -m "not integration and not e2e"
```

### Run integration tests
```bash
pytest -m integration
```

### Run E2E tests
```bash
pytest -m e2e
```

### Run performance tests
```bash
pytest -m performance
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### Run specific test file
```bash
pytest tests/test_database_consistency.py
```

### Run specific test
```bash
pytest tests/test_database_consistency.py::TestDatabaseConsistency::test_post_saved_to_both_databases
```

## Test Configuration

### pytest.ini
Main pytest configuration. By default, integration and e2e tests are skipped.

### pyproject.toml
Contains coverage configuration and pytest markers.

## Test Files

### Critical Tests (P0)
- `test_database_consistency.py`: SQLite ↔ Supabase sync consistency
- `test_transactions.py`: Transaction handling and rollback scenarios
- `test_database_sync.py`: Database sync behavior (existing, enhanced)

### Coverage Tests (P1)
- `test_e2e_workflows.py`: End-to-end workflow tests
- `test_automated_checklist.py`: Automated tests from manual checklist

### Performance Tests (P2)
- `test_performance.py`: Performance benchmarks and load tests

## CI/CD

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests

See `.github/workflows/ci.yml` for CI configuration.

## Coverage Targets

- **Target**: 80%+ coverage
- **Current**: Check with `pytest --cov=src --cov-report=term-missing`

## Writing Tests

### Unit Test Example
```python
def test_example():
    """Test description"""
    assert True
```

### Integration Test Example
```python
@pytest.mark.integration
def test_database_operation():
    """Test with database"""
    # Test code
    assert True
```

### E2E Test Example
```python
@pytest.mark.e2e
def test_full_workflow():
    """Test complete workflow"""
    # Test code
    assert True
```

## Test Fixtures

Common fixtures are in `conftest.py`:
- `sample_post`: Sample post data
- `test_data_dir`: Test data directory

## System Validation

### Running System Validation

```bash
# Run comprehensive system validation
python scripts/validation/system_validation.py

# Results saved to docs/VALIDATION_RESULTS.md
```

**What It Validates**:
- Database connection
- Supabase connection
- Analysis pipeline (10 posts)
- AI field parsing (key_concepts, tags, action_items)
- Collection pipeline
- API endpoints

**Expected Duration**: 5-10 minutes

### Validation Results

Results are saved to:
- `docs/VALIDATION_RESULTS.md` - Markdown report
- Console output - Real-time progress

## Test Data

### Required Test Data

- **Posts**: 10+ posts in database for analysis testing
- **Database**: `beyondlines.db` file (auto-created if missing)

### Optional Test Data

- **Supabase**: Test project (for sync tests)
- **AI Credentials**: Gemini/Mistral/Ollama keys (for analysis tests)
- **Platform Credentials**: Twitter/Reddit/Threads (for collection tests)
- **API Key**: `API_KEY` for API authentication tests

### Creating Test Data

```python
from src.services.new_database_manager import get_database_manager

db = get_database_manager()
test_post = {
    "post_id": "test_123",
    "platform": "twitter",
    "content": "Test post content",
    "author": "test_user",
    "url": "https://twitter.com/test/status/123",
}
db.add_post(test_post)
```

## Test Documentation

### Additional Resources

- **Test Matrix**: See `docs/TEST_MATRIX.md` for comprehensive test coverage
- **Test Runbook**: See `docs/TEST_RUNBOOK.md` for detailed test procedures
- **Validation Results**: See `docs/VALIDATION_RESULTS.md` for latest validation
- **Test Results**: See `docs/TEST_RESULTS.md` for test execution results

## Notes

- Integration tests may require test database credentials
- E2E tests require full system setup
- Performance tests are marked as `slow` and may take longer
- System validation creates test data automatically if needed
- Some tests skip gracefully if dependencies are missing

## Troubleshooting

### Common Issues

1. **Database errors**: Ensure `beyondlines.db` exists and is writable
2. **Import errors**: Ensure project root is in Python path
3. **Timeout errors**: Increase timeout values or check AI service availability
4. **API errors**: Start API server before running API tests

See `docs/TEST_RUNBOOK.md` for detailed troubleshooting guide.
