# Codebase Cleanup Plan

## Phase 0: Root Directory Cleanup (Immediate)

### 0.1 Organize Root Directory (COMPLETED)
- [x] Created `scripts/organize_root.py` to automate file organization
- [x] Moved all Python modules into `src/` directory
- [x] Moved all scripts into `scripts/` directory
- [x] Moved configuration files into `config/` directory
- [x] Moved documentation files into `docs/` directory
- [x] Moved test files into `tests/` directory
- [x] Moved data files into `data/` directory
- [x] Created `assets/` directory for static files
- [x] Created `requirements/` directory for dependency files
- [x] Moved `.env.example` to `config/`
- [x] Moved all `*.py` files from root to appropriate directories
- [x] Updated all imports to reflect new file locations

### 0.2 File Naming and Organization (COMPLETED)
- [x] Created `scripts/cleanup_files.py` to automate file cleanup
- [x] Renamed files to follow snake_case convention
- [x] Removed version suffixes (_v2, _new, etc.)
- [x] Removed backup files (*.bak, *.old, *.backup)
- [x] Removed temporary files (*.tmp, *.swp, *.swo)
- [x] Added IDE-specific files to .gitignore
- [x] Removed duplicate files
- [x] Removed unused files
- [x] Added large binary files to .gitignore
- [x] Added sensitive data patterns to .gitignore
- [x] Added compiled Python files to .gitignore

### 0.3 Documentation (COMPLETED)
- [x] Updated README.md with new project structure
- [x] Documented the purpose of each top-level directory
- [x] Added CONTRIBUTING.md information to README
- [x] Documented environment setup process
- [x] Documented deployment process
- [x] Documented testing process
- [x] Documented development workflow
- [x] Documented coding standards

## Phase 1: Environment and Dependencies

### 1.1 Virtual Environment (COMPLETED)
- [x] Created and documented virtual environment setup in README
- [x] Added requirements-dev.txt for development dependencies
- [x] Documented Python version requirements (Python 3.9+)
- [x] Added Python version check in setup instructions

### 1.2 Dependency Management (COMPLETED)
- [x] Created requirements-dev.txt with development dependencies
- [x] Pinned all production dependencies with exact versions
- [x] Added dependency management documentation
- [x] Created dependency update automation script (scripts/update_deps.py)
- [x] Configured pre-commit hooks for code quality
- [x] Documented development setup process
- [x] Added dependency update process documentation
- [x] Added security update guidelines

### 1.3 Development Workflow (COMPLETED)
- [x] Set up CI/CD pipeline with GitHub Actions
- [x] Documented code review process and guidelines
- [x] Added pull request template
- [x] Set up automated testing and code quality checks
- [x] Added security scanning in CI
- [x] Set up automated documentation deployment

### 1.4 Release Management (COMPLETED)
- [x] Documented release process
- [x] Set up Semantic Versioning (SemVer)
- [x] Created release checklist
- [x] Documented hotfix process
- [x] Set up CHANGELOG.md following Keep a Changelog
- [x] Documented rollback procedures

### 1.5 Code Quality and Standards (COMPLETED)
- [x] Set up code coverage reporting with `.coveragerc`
- [x] Documented code style guidelines in `docs/code_style_guide.md`
- [x] Set up Sphinx API documentation
- [x] Configured automated code formatting with Black
- [x] Documented error handling standards
- [x] Added performance guidelines

### 1.6 Testing Strategy (COMPLETED)
- [x] Set up unit test framework with pytest
- [x] Added integration test structure
- [x] Configured test coverage reporting
- [x] Set up test fixtures
- [x] Documented testing guidelines in `docs/testing_guide.md`
- [x] Added performance testing guidelines

### 1.7 Documentation (COMPLETED)
- [x] Updated README with comprehensive documentation section
- [x] Consolidated roadmap files into `docs/roadmap.md`
- [x] Moved and updated coding standards to `docs/development/CODING_STANDARDS.md`
- [x] Added architecture overview (`docs/architecture.md`)
- [x] Documented configuration options (`docs/configuration_reference.md`)
- [x] Created user guide (`docs/user_guide.md`)
- [x] Added troubleshooting section to user guide
- [x] Documented deployment process in README

### 1.8 Deployment (NEXT)
- [ ] Document production deployment process
- [ ] Set up staging environment
- [ ] Configure monitoring and alerting
- [ ] Document backup and recovery
- [ ] Set up CI/CD pipeline
- [ ] Document scaling strategy

## Phase 1: File Structure Cleanup (Week 1)

### 1.1 Remove Duplicate/Redundant Files (COMPLETED)
- [x] Removed `working_reddit_extractor.py` (kept the one in `core/extraction/`)
- [x] Cleaned up unused files in `redundant/` directory (backed up to `redundant_backup.zip`)
- [x] Removed backup files (`.backup`, `.old`, etc.) - No backup files found
- [x] Removed any `_v2`, `_new`, or `_working` files after merging changes - No such files found
- [x] Removed duplicate `makefile_1` (kept the standard `Makefile`)
- [x] Removed duplicate `streamlit_secrets_ready_1.toml` (kept the standard `streamlit_secrets.toml`)
- [x] Renamed `readme_1.md` to `README.md` to follow standard naming conventions
- [x] Removed empty `data/prismind_1.db` (kept the main `prismind.db`)
- [x] Renamed documentation files to remove `_1` suffix:
  - `docs/cleanup_plan_1.md` → `docs/cleanup_plan.md`
  - `docs/contributing_1.md` → `docs/contributing.md`
  - `docs/use_cases_1.md` → `docs/use_cases.md`
- [x] Removed log file `logs/assets/images/auth_failure_attempt_1.png`
- [x] Removed `redundant_backup.zip` after confirming cleanup
- [x] Removed duplicate `.pre_commit_config.yaml` (kept the more comprehensive `.pre-commit-config.yaml`)
- [x] Removed empty `requirements/` directory
- [x] Removed empty `scripts/utilities/` directory
- [x] Removed empty unused directories:
  - `core/`
  - `services/`
  - `src/api/`
  - `src/core/analysis/unused/`
  - `src/core/models/`
  - `src/utils/`
  - `tests/integration/`
  - `tests/unit/`
- [x] Cleaned up Python cache files (`__pycache__` directories)

### 1.2 Reorganize Project Structure (COMPLETED)
- [x] Created new directory structure
- [x] Moved core modules to `src/core/`
- [x] Moved services to `src/services/`
- [x] Moved web interface to `src/web/`
```
prismind/
├── src/                      # Main source code
│   ├── api/                  # API endpoints
│   ├── core/                 # Core business logic
│   │   ├── analysis/         # AI analysis modules
│   │   ├── extraction/       # Platform extractors
│   │   └── models/           # Data models
│   ├── services/             # Application services
│   ├── utils/                # Utility functions
│   └── web/                  # Web interface (Streamlit)
├── tests/                    # Test files
├── config/                   # Configuration files
├── scripts/                  # Utility scripts
└── docs/                     # Documentation
```

### 1.3 Split Large Files (COMPLETED)
- [x] Broke down `app.py` into smaller modules:
  - [x] `web/components/dashboard.py` - Streamlit UI components
  - [x] `web/components/sidebar.py` - Sidebar navigation and controls
  - [x] `services/collection_service.py` - Collection functionality
  - [x] `services/database_manager.py` - Database operations
- [x] Split any other files over 300 lines

### 1.4 Standardize Naming Conventions
- [ ] Use consistent naming (snake_case for files and functions, PascalCase for classes)
- [ ] Update all imports to use absolute paths
- [ ] Ensure consistent naming across the codebase

## Phase 2: Environment and Dependencies (Week 2)

### 2.1 Environment Setup
- [ ] Create `.env.example` with all required variables
- [ ] Add validation for required environment variables
- [ ] Document environment setup in README.md

### 2.2 Dependency Management
- [ ] Pin all dependencies with exact versions
- [ ] Remove unused dependencies
- [ ] Update outdated packages
- [ ] Add development dependencies to `dev-requirements.txt`

## Phase 3: Code Quality (Week 3)

### 3.1 Linting and Formatting
- [ ] Set up pre-commit hooks
- [ ] Configure Black for code formatting
- [ ] Add isort for import sorting
- [ ] Add flake8 for linting

### 3.2 Type Checking
- [ ] Add mypy configuration
- [ ] Add type hints to all functions
- [ ] Fix all type errors

### 3.3 Testing
- [ ] Set up pytest
- [ ] Add unit tests for core functionality
- [ ] Add integration tests
- [ ] Add test coverage reporting

## Phase 4: Documentation (Week 4)

### 4.1 Code Documentation
- [ ] Add Google-style docstrings to all public functions/classes
- [ ] Add module-level docstrings
- [ ] Document complex algorithms

### 4.2 Project Documentation
- [ ] Update README.md
- [ ] Add CONTRIBUTING.md
- [ ] Document architecture decisions (ADRs)
- [ ] Create API documentation

## Phase 5: Final Cleanup (Week 5)

### 5.1 Code Review
- [ ] Review all changes
- [ ] Get feedback from team
- [ ] Address all review comments

### 5.2 Performance Optimization
- [ ] Profile the application
- [ ] Optimize slow functions
- [ ] Add caching where appropriate

### 5.3 Final Checks
- [ ] Ensure all tests pass
- [ ] Verify documentation is up to date
- [ ] Update CHANGELOG.md

## How to Use This Plan
1. Check off items as you complete them
2. Add any additional tasks that come up
3. Update estimates as needed
4. Keep the team updated on progress

## Notes
- Each task should be small and focused
- No task should take more than 4 hours
- If a task is too big, break it down further
- Update this document as the plan evolves
