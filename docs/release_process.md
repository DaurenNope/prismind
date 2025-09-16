# Release Management

This document outlines the release process for the PrisMind project, following Semantic Versioning (SemVer).

## Versioning Strategy

We follow [Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible functionality
- **PATCH** version for backward-compatible bug fixes

## Release Schedule

- **Patch Releases**: As needed for critical bug fixes
- **Minor Releases**: Monthly, on the first Monday
- **Major Releases**: As needed for significant changes

## Pre-Release Checklist

### Code Quality
- [ ] All tests pass
- [ ] Code coverage meets threshold (min 80%)
- [ ] No open high-priority bugs
- [ ] Security scans clean
- [ ] Dependencies up to date

### Documentation
- [ ] README updated
- [ ] CHANGELOG updated
- [ ] API documentation current
- [ ] Upgrade instructions written

### Process
- [ ] Feature freeze in effect
- [ ] All PRs merged to `main`
- [ ] Release branch created
- [ ] Version numbers updated

## Release Process

1. **Prepare Release Branch**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b release/vX.Y.Z
   ```

2. **Update Version**
   - Update `__version__` in `src/__init__.py`
   - Update version in `pyproject.toml`
   - Update any other version references

3. **Update CHANGELOG.md**
   - Add new version header
   - List all changes (features, fixes, breaking changes)
   - Include PR/issue references

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "chore: prepare release vX.Y.Z"
   ```

5. **Create Release PR**
   ```bash
   git push -u origin release/vX.Y.Z
   # Create PR from release/vX.Y.Z to main
   ```

6. **Review and Merge**
   - Get approval from at least one maintainer
   - Ensure all CI checks pass
   - Squash and merge the PR

7. **Create Git Tag**
   ```bash
   git checkout main
   git pull origin main
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

8. **Publish to PyPI**
   ```bash
   python -m pip install --upgrade build twine
   python -m build
   twine upload dist/*
   ```

9. **Update Documentation**
   - Deploy updated documentation
   - Update any version-specific docs

10. **Announce Release**
    - Create GitHub Release with changelog
    - Notify stakeholders
    - Post on community channels

## Hotfix Process

For critical bug fixes to production:

1. **Create Hotfix Branch**
   ```bash
   git checkout -b hotfix/vX.Y.Z main
   ```

2. **Make Fixes**
   - Apply minimal changes needed
   - Add tests
   - Update CHANGELOG

3. **Release**
   - Follow standard release process
   - Merge to both `main` and `develop`
   - Increment PATCH version

## Rollback Procedure

If a release has critical issues:

1. **Revert Release**
   ```bash
   git revert <release-commit> --no-commit
   git commit -m "revert: vX.Y.Z due to critical issue #123"
   git push origin main
   ```

2. **Yank PyPI Release**
   ```bash
   twine upload --skip-existing --repository-url https://pypi.org/legacy/ dist/*
   ```

3. **Communicate**
   - Update GitHub release notes
   - Notify users
   - Document the issue and resolution

## Post-Release Tasks

- [ ] Update development version in `main`
- [ ] Close related issues/PRs
- [ ] Archive release branch
- [ ] Update roadmap
- [ ] Schedule next release planning
