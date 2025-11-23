# Test Runbook

**Date**: 2025-01-11  
**Purpose**: Actionable guide for running tests and validating the BEYONDLINES system

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Ensure test database exists
# (Uses beyondlines.db - will create if missing)

# Set up environment (optional)
cp .env.example .env
# Edit .env with test credentials if needed
```

### Run All Tests

```bash
# Quick smoke tests (5 minutes)
pytest tests/test_integration_collection.py tests/test_integration_analysis.py -v

# Full test suite (30 minutes)
pytest --cov=src --cov-report=term-missing -v

# System validation (comprehensive)
python scripts/validation/system_validation.py
```

## Test Procedures

### 1. System Validation

**Purpose**: Validate all system components are working correctly

**Command**:
```bash
python scripts/validation/system_validation.py
```

**Expected Output**:
- Database connection: ✅ Success
- Supabase connection: ✅ Success or ⚠️ Warning
- Analysis pipeline: ✅ Success
- AI field parsing: ✅ Success or ⚠️ Warning
- Collection pipeline: ✅ Success
- API endpoints: ✅ Success or ⚠️ Warning

**Results**: Saved to `docs/VALIDATION_RESULTS.md`

**Troubleshooting**:
- Database connection fails: Check `beyondlines.db` exists
- Supabase connection fails: Check credentials in `.env`
- Analysis fails: Check AI service credentials
- API endpoints fail: Start API server with `python -m src.api.main`

### 2. Integration Tests

#### Collection Integration Tests

**Purpose**: Test collection → database flow

**Command**:
```bash
pytest tests/test_integration_collection.py -v
```

**What It Tests**:
- Collection service initialization
- Post collection from platforms
- Database storage
- Duplicate detection
- Error handling

**Expected Duration**: 2-5 minutes

**Troubleshooting**:
- Collection fails: Check platform credentials in `.env`
- Duplicate detection issues: Normal for existing posts
- Database errors: Check database permissions

#### Analysis Integration Tests

**Purpose**: Test analysis → database flow

**Command**:
```bash
pytest tests/test_integration_analysis.py -v
```

**What It Tests**:
- Analysis pipeline execution
- AI field extraction (key_concepts, tags, action_items)
- Database storage of analysis results
- Error handling

**Expected Duration**: 5-10 minutes (depends on AI service)

**Troubleshooting**:
- Analysis fails: Check AI service credentials (Gemini/Mistral/Ollama)
- Fields missing: Check AI service response format
- Timeouts: Increase timeout values in test

#### Publishing Integration Tests

**Purpose**: Test publishing workflow

**Command**:
```bash
pytest tests/test_integration_publishing.py -v
```

**What It Tests**:
- Rewrite candidate identification
- Scheduling workflow
- Publishing error handling

**Expected Duration**: 1-2 minutes

**Troubleshooting**:
- Rewrite tests skip: Normal if no high-value posts
- Scheduling tests skip: Normal if Supabase not configured

#### API Integration Tests

**Purpose**: Test API endpoints

**Command**:
```bash
# Start API server first (in separate terminal)
python -m src.api.main

# Then run tests
pytest tests/test_integration_api.py -v
```

**What It Tests**:
- API endpoint availability
- Authentication requirements
- Response formats
- Error handling

**Expected Duration**: 1-2 minutes

**Troubleshooting**:
- Connection errors: Ensure API server is running
- Auth failures: Set `API_KEY` in `.env` or test environment
- 401 errors: Normal for protected endpoints without auth

### 3. Unit Tests

**Purpose**: Test individual components in isolation

**Command**:
```bash
# All unit tests
pytest -m "not integration and not e2e" -v

# Specific component
pytest tests/test_ai_analyzer.py -v
pytest tests/test_collection.py -v
pytest tests/test_rewriter.py -v
```

**Expected Duration**: 5-10 minutes

### 4. End-to-End Tests

**Purpose**: Test complete workflows

**Command**:
```bash
pytest tests/test_e2e_workflows.py -v
```

**Expected Duration**: 10-20 minutes

**Note**: May require live credentials and external services

## Test Environment Setup

### Local Development Environment

```bash
# 1. Clone repository
git clone <repo-url>
cd prismind

# 2. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your credentials (optional for most tests)

# 5. Set up test database
# Tests will use existing beyondlines.db or create new one

# 6. Run tests
pytest -v
```

### CI/CD Environment

Tests run automatically on:
- Push to main/develop branches
- Pull requests

See `.github/workflows/ci.yml` for configuration.

## Test Data Setup

### Minimum Test Data

- **Posts**: 10+ posts in database (collected or manually added)
- **Database**: `beyondlines.db` file (auto-created if missing)

### Optional Test Data

- **Supabase**: Test project with posts table
- **AI Credentials**: Gemini/Mistral/Ollama API keys
- **Platform Credentials**: Twitter/Reddit/Threads credentials
- **API Key**: `API_KEY` for authentication tests

### Creating Test Data

```python
# Add test posts manually
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

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Error**: `sqlite3.OperationalError: unable to open database file`

**Solution**:
```bash
# Check database file exists
ls -la beyondlines.db

# Check file permissions
chmod 644 beyondlines.db

# Create database if missing
python -c "from src.services.new_database_manager import get_database_manager; db = get_database_manager(); print('Database initialized')"
```

#### 2. Supabase Connection Errors

**Error**: `Missing Supabase credentials`

**Solution**:
```bash
# Check .env file
cat .env | grep SUPABASE

# Add credentials if missing
echo "SUPABASE_URL=https://your-project.supabase.co" >> .env
echo "SUPABASE_SERVICE_ROLE_KEY=your-key" >> .env
```

**Note**: Supabase is optional - tests will skip if not configured

#### 3. AI Service Errors

**Error**: `Gemini API error` or `Mistral API error`

**Solution**:
```bash
# Check API keys in .env
cat .env | grep GEMINI
cat .env | grep MISTRAL

# Add keys if missing (or tests will use Ollama fallback)
echo "GEMINI_API_KEY=your-key" >> .env
echo "MISTRAL_API_KEY=your-key" >> .env
```

**Note**: Tests use Ollama as fallback if cloud APIs unavailable

#### 4. Import Errors

**Error**: `ModuleNotFoundError`

**Solution**:
```bash
# Ensure project root is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in development mode
pip install -e .

# Reinstall dependencies
pip install -r requirements.txt
```

#### 5. Test Timeouts

**Error**: `TimeoutError` or tests hang

**Solution**:
```bash
# Run tests with timeout
pytest --timeout=300 tests/test_integration_analysis.py -v

# Or increase timeout in test file
# Look for timeout parameters in test functions
```

#### 6. API Server Not Running

**Error**: `Connection refused` in API tests

**Solution**:
```bash
# Start API server in separate terminal
python -m src.api.main

# Wait for "API will be available at: http://localhost:8000"
# Then run tests
pytest tests/test_integration_api.py -v
```

## Test Maintenance

### Adding New Tests

1. **Create test file** in `tests/` directory
2. **Use pytest markers**:
   ```python
   @pytest.mark.integration
   async def test_new_feature():
       # Test code
   ```
3. **Follow naming conventions**: `test_*.py`
4. **Add to test matrix**: Update `docs/TEST_MATRIX.md`

### Updating Test Data

```bash
# Refresh test database
rm beyondlines.db
python scripts/collection/run_full_collection.py

# Or manually add test posts
python -c "from src.services.new_database_manager import get_database_manager; db = get_database_manager(); # Add posts"
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Execution Best Practices

### 1. Run Tests Locally Before Committing

```bash
# Quick check
pytest tests/test_integration_collection.py -v

# Full check
pytest --cov=src -v
```

### 2. Run System Validation After Changes

```bash
python scripts/validation/system_validation.py
```

### 3. Check Test Results

```bash
# View validation results
cat docs/VALIDATION_RESULTS.md

# View coverage report
open htmlcov/index.html
```

### 4. Fix Test Failures

1. **Identify failing test**: Check test output
2. **Reproduce issue**: Run test individually
3. **Debug**: Add logging or breakpoints
4. **Fix**: Update code or test
5. **Verify**: Re-run test
6. **Document**: Update test documentation if needed

## Continuous Integration

Tests run automatically in CI/CD:

- **On Push**: All unit and integration tests
- **On PR**: Full test suite with coverage
- **On Merge**: Full validation + deployment tests

### CI Test Configuration

```yaml
# .github/workflows/ci.yml
- name: Run tests
  run: |
    pytest --cov=src --cov-report=xml -v
```

## Test Metrics

### Key Metrics to Track

- **Test Pass Rate**: Percentage of passing tests
- **Test Execution Time**: Time to run full suite
- **Code Coverage**: Percentage of code covered
- **Test Reliability**: Consistency of test results

### Monitoring

- **Test Results**: Track in CI/CD dashboard
- **Coverage Reports**: Track over time
- **Validation Results**: Track in `docs/VALIDATION_RESULTS.md`

## Quick Reference

### Test Commands Cheat Sheet

```bash
# Quick smoke tests
pytest tests/test_integration_collection.py -v

# Full test suite
pytest --cov=src -v

# Specific test file
pytest tests/test_integration_analysis.py -v

# Specific test
pytest tests/test_integration_analysis.py::TestAnalysisPipelineIntegration::test_analysis_pipeline_full_flow -v

# With coverage
pytest --cov=src --cov-report=html

# System validation
python scripts/validation/system_validation.py

# All integration tests
pytest -m integration -v

# All unit tests
pytest -m "not integration and not e2e" -v
```

### Environment Variables

```bash
# Required for most tests
# None required - tests use existing database

# Optional (for full functionality)
API_KEY=your-api-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key
GEMINI_API_KEY=your-key
MISTRAL_API_KEY=your-key
```

## Support

For test issues:
1. Check troubleshooting section above
2. Review test logs for errors
3. Check `docs/VALIDATION_RESULTS.md` for system status
4. Review test documentation in `tests/README.md`






