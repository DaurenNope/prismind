# Code Style Guide

This document outlines the coding standards and best practices for the PrisMind project.

## Python Style

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with the following additions:

### General
- **Line Length**: 88 characters (Black default)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes (`"`) for strings, single quotes (`'`) for docstrings
- **Imports**: Grouped and ordered as follows:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
  
  Each group separated by a blank line, sorted alphabetically.

### Naming Conventions
- **Variables and functions**: `lowercase_with_underscores`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Classes**: `PascalCase`
- **Private**: Prefix with `_` for non-public methods/variables
- **Type variables**: Short uppercase names, e.g., `T = TypeVar('T')`

### Type Annotations
- Use type hints for all function/method signatures
- Use `typing` module for complex types
- Prefer `list[Type]` over `List[Type]` (Python 3.9+)
- Use `Optional[Type]` for values that can be `None`
- Use `@override` decorator for method overrides

## Documentation

### Docstrings
Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Short description of what the function does.

    Longer description with more details about the function's functionality.

    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter.

    Returns:
        Description of the return value.

    Raises:
        ValueError: If something bad happens.
    """
```

### Inline Comments
- Use sparingly and only when necessary
- Explain "why" not "what"
- Keep comments up-to-date with code changes

## Error Handling

- Use specific exceptions when possible
- Include meaningful error messages
- Log errors with appropriate context
- Use custom exceptions for domain-specific errors

## Testing

### Naming
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Structure
- One test class per module/class being tested
- Use fixtures for common setup/teardown
- Follow Arrange-Act-Assert pattern
- Use descriptive test names

## Logging

- Use the `logging` module
- Configure logging at the module level:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```
- Use appropriate log levels:
  - DEBUG: Detailed information for debugging
  - INFO: Confirmation that things are working as expected
  - WARNING: Indication that something unexpected happened
  - ERROR: Serious problem, the software hasn't been able to perform some function
  - CRITICAL: A serious error, the program itself may be unable to continue running

## Performance

- Use built-in functions and libraries when possible
- Avoid premature optimization
- Use generators for large datasets
- Consider time complexity of operations
- Profile before optimizing

## Security

- Never hardcode secrets
- Use environment variables for configuration
- Validate all inputs
- Sanitize data before processing
- Keep dependencies updated

## Git Workflow

### Commit Messages
- Use the format: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore
- Keep the subject line under 50 characters
- Use the body to explain what and why, not how

### Branches
- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `hotfix/*`: Critical production fixes

## Code Review

- Be respectful and constructive
- Focus on code, not the author
- Explain the reasoning behind suggestions
- Suggest improvements, not just point out issues
- Acknowledge good patterns and solutions
