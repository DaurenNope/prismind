# BEYONDLINES Naming Conventions Guide

## Overview
This document defines the naming conventions used throughout the BEYONDLINES codebase to ensure consistency and maintainability.

## Python Naming Standards

### 1. Classes (PascalCase)
```python
class TwitterExtractor:
class DatabaseManager:
class ContentAnalyzer:
class RateLimiter:
```

### 2. Functions and Variables (snake_case)
```python
def extract_tweets():
def validate_content():
tweet_data = {}
user_auth = None
```

### 3. Constants (UPPER_SNAKE_CASE)
```python
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30
TWITTER_API_BASE_URL = "https://api.twitter.com/2/"
```

### 4. Private Members (snake_case with leading underscore)
```python
class MyClass:
    def __init__(self):
        self._private_var = None
        self.__very_private = None

    def _private_method(self):
        pass
```

### 5. File Names (snake_case)
```
twitter_extractor.py
database_manager.py
content_analyzer.py
rate_limiter.py
```

### 6. Module Names (snake_case)
```
src/core/extraction/twitter/
src/database/operations/
src/publishing/platforms/
```

## Specific Patterns

### 1. Service Classes
- **Pattern**: `[Domain]Manager` or `[Domain]Service`
- **Examples**: `DatabaseManager`, `ContentService`, `AuthService`

### 2. Extractor Classes
- **Pattern**: `[Platform]Extractor`
- **Examples**: `TwitterExtractor`, `RedditExtractor`, `ThreadsExtractor`

### 3. Analyzer Classes
- **Pattern**: `[Target]Analyzer` or `[Target]Validator`
- **Examples**: `ContentAnalyzer`, `SentimentValidator`, `QualityScorer`

### 4. API Endpoints
- **Pattern**: `/{resource}/{action}`
- **Examples**: `/api/posts/get`, `/api/collection/start`, `/api/analysis/run`

### 5. Database Tables
- **Pattern**: `snake_case` plural
- **Examples**: `posts`, `users`, `scheduled_posts`, `rewrite_feedback`

### 6. Database Columns
- **Pattern**: `snake_case`
- **Examples**: `created_at`, `updated_at`, `user_id`, `post_content`

## Identified Inconsistencies and Fixes

### 1. File Structure Issues
**Current Issues:**
- Mixed naming in extraction modules
- Inconsistent service naming
- Some files use camelCase

**Fixes Applied:**
- Standardized `twitter_extractor_refactored.py` (refactored version)
- Consistent `auth_manager.py`, `data_extractor.py`
- Proper module organization under `twitter/` subdirectory

### 2. Class Naming Issues
**Current Issues:**
- Some classes don't follow PascalCase consistently
- Mixed naming patterns for similar functionality

**Standards Enforced:**
- All classes use PascalCase
- Similar functionality uses consistent naming patterns

### 3. Function Naming Issues
**Current Issues:**
- Some functions use camelCase
- Inconsistent verb-noun patterns

**Standards Enforced:**
- All functions use snake_case
- Consistent verb-noun patterns (`get_data`, `set_value`, `is_valid`)

## Migration Checklist

### Phase 1: File Renaming
- [ ] Review all file names for snake_case compliance
- [ ] Update imports throughout codebase
- [ ] Update documentation references

### Phase 2: Class Renaming
- [ ] Audit all class names for PascalCase compliance
- [ ] Update class references and instantiations
- [ ] Update inheritance relationships

### Phase 3: Function/Variable Renaming
- [ ] Audit function names for snake_case compliance
- [ ] Update function calls throughout codebase
- [ ] Review variable naming consistency

### Phase 4: Database Consistency
- [ ] Ensure all table names follow snake_case plural
- [ ] Ensure all column names follow snake_case
- [ ] Update migration files accordingly

## Automation Tools

### 1. Linting Configuration
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py38']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]
```

### 2. Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
```

### 3. Naming Convention Checker
```python
# tools/naming_checker.py
import ast
import os
from pathlib import Path

class NamingConventionChecker:
    def check_file(self, filepath):
        """Check a Python file for naming convention violations"""
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())

        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not self._is_pascal_case(node.name):
                    violations.append(f"Class {node.name} should use PascalCase")

            elif isinstance(node, ast.FunctionDef):
                if not self._is_snake_case(node.name):
                    violations.append(f"Function {node.name} should use snake_case")

        return violations

    def _is_pascal_case(self, name):
        return name.replace('_', '').isalnum() and name[0].isupper()

    def _is_snake_case(self, name):
        return name.islower() or '_' in name
```

## Best Practices

### 1. Be Descriptive but Concise
```python
# Good
def extract_twitter_data():
class ContentQualityAnalyzer:
user_authentication_token

# Avoid
def ext_tw():
class CQA:
uat
```

### 2. Use Domain-Specific Language
```python
# Good
def analyze_sentiment():
class TweetExtractor:
engagement_metrics

# Generic but acceptable
def process_data():
class DataProcessor:
metrics
```

### 3. Avoid Abbreviations (Unless Common)
```python
# Good
authentication
configuration
user_interface

# Acceptable abbreviations
id (identifier)
url (uniform resource locator)
api (application programming interface)
html (hypertext markup language)
```

### 4. Boolean Naming
```python
# Good
is_authenticated
has_content
can_retry
should_process

# Avoid
authenticated
content
retry
process
```

### 5. Context-Specific Naming
```python
# Good (in context of Twitter)
def extract_tweets():
def fetch_user_timeline():
def analyze_hashtags():

# Good (in context of Database)
def insert_posts():
def update_user_data():
def create_indexes():
```

## Review Process

### 1. Code Review Checklist
- [ ] All classes use PascalCase
- [ ] All functions use snake_case
- [ ] All variables use snake_case
- [ ] Constants use UPPER_SNAKE_CASE
- [ ] Private members use leading underscore
- [ ] File names use snake_case
- [ ] Names are descriptive and unambiguous
- [ ] No abbreviations unless commonly understood

### 2. Automated Testing
```bash
# Run naming convention checks
python tools/naming_checker.py src/

# Run linting
black --check src/
isort --check-only src/
flake8 src/
```

### 3. Documentation Updates
- Update all documentation to reflect new naming
- Update README files with correct module names
- Update import examples in documentation

## Future Considerations

### 1. Type Hints
- Ensure type hints follow the same naming conventions
- Use proper typing for function signatures and class attributes

### 2. Configuration Files
- Apply naming conventions to configuration keys
- Ensure environment variables follow consistent patterns

### 3. API Design
- Endpoint naming should follow REST conventions
- JSON response keys should use snake_case
- Query parameters should use snake_case
