# Coding Standards and Best Practices

## Table of Contents
- [File Organization](#file-organization)
- [Code Style](#code-style)
- [Git Workflow](#git-workflow)
- [Testing](#testing)
- [Documentation](#documentation)
- [Security](#security)
- [Performance](#performance)
- [Code Review](#code-review)

## File Organization

### General Rules
- **Single Source of Truth**: Each logical component should exist in exactly one file
- **No Duplicates**: No `_working.py`, `_v2.py`, or similar duplicates
- **File Size**: Maximum 300 lines per file (excluding tests and auto-generated code)
- **Directory Structure**: Follow the project's established structure strictly

### Naming Conventions
- **Files**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `lowercase_with_underscores()`
- **Variables**: `lowercase_with_underscores`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private**: `_private_variable` (single underscore)
- **Protected**: `__protected_variable` (double underscore)

## Code Style

### General
- **PEP 8 Compliance**: Follow PEP 8 guidelines strictly
- **Type Hints**: All functions and methods must have type hints
- **Docstrings**: Google-style docstrings for all public functions/classes
- **Line Length**: Maximum 88 characters per line (Black formatter default)
- **Imports**: Grouped and sorted (standard library, third-party, local)

### Python Specific
- Use f-strings for string formatting (Python 3.6+)
- Use list/dict/set comprehensions where appropriate
- Prefer `pathlib` over `os.path` for filesystem operations
- Use context managers for resource management
- Handle exceptions specifically, don't use bare `except`

## Git Workflow

### Branch Naming
- `feature/` - New features
- `bugfix/` - Bug fixes
- `hotfix/` - Critical production fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test-related changes

### Commit Messages
Follow the Conventional Commits specification:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvements
- `test`: Adding or modifying tests
- `chore`: Changes to the build process or auxiliary tools

### Pull Requests
- One logical change per PR
- Reference relevant issues
- Include tests for new features/bug fixes
- Update documentation as needed
- Get at least one code review before merging

## Testing

### General Guidelines
- Write tests for all new code
- Follow the Arrange-Act-Assert pattern
- Tests should be isolated and independent
- Test edge cases and error conditions
- Use descriptive test names

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

### Test Naming
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

## Documentation

### Code Documentation
- Module-level docstrings
- Class and method docstrings
- Type hints for all function signatures
- Inline comments for complex logic

### Project Documentation
- Keep README.md up to date
- Document all environment variables
- Document setup and deployment procedures
- Maintain a changelog

## Security

### General
- Never commit sensitive data (API keys, passwords, etc.)
- Use environment variables for configuration
- Validate all user input
- Use parameterized queries for database access
- Keep dependencies up to date

### Authentication/Authorization
- Use strong password hashing (bcrypt, Argon2)
- Implement proper session management
- Use HTTPS in production
- Implement rate limiting

## Performance

### General Guidelines
- Profile before optimizing
- Use appropriate data structures
- Minimize database queries
- Use caching where appropriate
- Be mindful of memory usage

### Performance Anti-patterns to Avoid
- N+1 queries
- Loading too much data into memory
- Inefficient algorithms
- Unnecessary computations in loops

## Code Review

### Review Checklist
- [ ] Code follows style guidelines
- [ ] No commented-out code
- [ ] Proper error handling
- [ ] Tests are included
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed

### Review Etiquette
- Be respectful and constructive
- Focus on the code, not the person
- Explain the "why" behind suggestions
- Acknowledge good patterns
- Keep discussions professional

## Continuous Integration
- All tests must pass
- Code coverage should not decrease
- Static analysis must pass
- Documentation builds successfully
- No merge conflicts

## Dependencies
- Pin all direct dependencies
- Document all dependencies
- Keep dependencies up to date
- Audit for security vulnerabilities

## Maintenance
- Keep the codebase clean
- Remove unused code
- Update documentation
- Address technical debt regularly

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
