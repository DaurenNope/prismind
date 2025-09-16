# Dependency Management

This document outlines the dependency management strategy for the PrisMind project.

## Overview

We use a two-tier dependency system:
- `requirements.txt`: Production dependencies with pinned versions
- `requirements-dev.txt`: Development dependencies (includes all production deps)

## Managing Dependencies

### Adding a New Dependency

1. **For production dependencies**:
   ```bash
   pip install <package>==<version>
   pip freeze | grep -i <package> >> requirements.txt
   ```

2. **For development dependencies**:
   ```bash
   pip install <package>==<version>
   pip freeze | grep -i <package> >> requirements-dev.txt
   ```

### Updating Dependencies

1. **Check for outdated packages**:
   ```bash
   python scripts/update_deps.py
   # Then select option 1
   ```

2. **Update a specific package**:
   ```bash
   pip install --upgrade <package>==<new-version>
   ```

3. **Update all requirements files**:
   ```bash
   python scripts/update_deps.py
   # Then select option 2
   ```

### Dependency Resolution

- We use `pip-tools` for dependency resolution (included in `requirements-dev.txt`)
- To update all dependencies while respecting version constraints:
  ```bash
  pip-compile --upgrade
  ```

## Version Pinning

- All production dependencies must have exact versions pinned
- Development dependencies should also be pinned when possible
- Use `~=` for compatible release versions when appropriate

## Security Updates

1. Regularly check for security vulnerabilities:
   ```bash
   pip-audit
   ```

2. Update vulnerable packages immediately
3. Run tests after each update

## Best Practices

- Always use virtual environments
- Never edit `requirements.txt` or `requirements-dev.txt` manually
- Document the reason for each dependency
- Keep dependencies to a minimum
- Review and update dependencies regularly
