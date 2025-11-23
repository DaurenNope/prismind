# Codebase Restructuring Migration Guide

**Date**: December 2024  
**Status**: ✅ Complete

## Overview

The codebase has been restructured from a flat, service-oriented architecture into a clear domain-driven design with proper separation of concerns.

## New Structure

```
src/
├── domain/              # Business domains
│   ├── collection/      # Collection domain
│   │   ├── services/
│   │   ├── extractors/
│   │   └── models.py
│   ├── analysis/       # Analysis domain
│   │   ├── services/
│   │   ├── analyzers/
│   │   └── models.py
│   ├── publishing/     # Publishing domain
│   │   ├── services/
│   │   ├── platforms/
│   │   └── models.py
│   └── intelligence/   # Intelligence domain
│       ├── agents/
│       ├── research/
│       └── models.py
│
├── infrastructure/     # Technical infrastructure
│   ├── database/
│   ├── messaging/
│   ├── monitoring/
│   └── observability/
│
├── application/        # Application layer
│   ├── api/
│   ├── orchestration/
│   └── automation/
│
└── shared/              # Shared utilities
    ├── utils/
    ├── config/
    └── exceptions/
```

## Migration Path

### Import Changes

All imports have been automatically updated. The following mappings show the changes:

#### Collection Domain
- `src.core.collection` → `src.domain.collection`
- `src.core.extraction` → `src.domain.collection.extractors`
- `src.services.collection` → `src.domain.collection.services`
- `src.services.unified_collection_service` → `src.domain.collection.services.unified_collection_service`

#### Analysis Domain
- `src.core.analysis` → `src.domain.analysis.analyzers`
- `src.services.analysis` → `src.domain.analysis.services`
- `src.services.analysis_runner` → `src.domain.analysis.services.analysis_runner`

#### Publishing Domain
- `src.publishing` → `src.domain.publishing` (no change in path, but now in domain structure)

#### Intelligence Domain
- `src.agents` → `src.domain.intelligence.agents`
- `src.research` → `src.domain.intelligence.research`
- `src.intelligence` → `src.domain.intelligence`

#### Infrastructure
- `src.database` → `src.infrastructure.database`
- `src.messaging` → `src.infrastructure.messaging`
- `src.monitoring` → `src.infrastructure.monitoring`
- `src.observability` → `src.infrastructure.observability`
- `src.storage` → `src.infrastructure.database.storage`

#### Application
- `src.api` → `src.application.api`
- `src.core.orchestration` → `src.application.orchestration`
- `src.orchestration` → `src.application.orchestration`
- `src.pipeline` → `src.application.automation`

#### Shared
- `src.utils` → `src.shared.utils`
- `src.core.schemas` → `src.shared.schemas`

### Backward Compatibility

Backward compatibility `__init__.py` files have been created in the old locations that redirect to the new structure. This ensures existing code continues to work during the transition period.

**Note**: These compatibility files should be removed after all code has been migrated to use the new import paths.

## File Moves

### Collection Domain
- `src/core/collection/*` → `src/domain/collection/`
- `src/core/extraction/*` → `src/domain/collection/extractors/`
- `src/services/collection/*` → `src/domain/collection/services/`
- `src/services/unified_collection_service.py` → `src/domain/collection/services/`
- `src/services/telegram_collection_commands.py` → `src/domain/collection/services/`

### Analysis Domain
- `src/core/analysis/*` → `src/domain/analysis/analyzers/`
- `src/services/analysis/*` → `src/domain/analysis/services/`
- `src/services/analysis_runner.py` → `src/domain/analysis/services/`

### Publishing Domain
- `src/publishing/*` → `src/domain/publishing/` (already in place)

### Intelligence Domain
- `src/agents/*` → `src/domain/intelligence/agents/`
- `src/research/*` → `src/domain/intelligence/research/`
- `src/intelligence/*` → `src/domain/intelligence/`

### Infrastructure
- `src/database/*` → `src/infrastructure/database/`
- `src/messaging/*` → `src/infrastructure/messaging/`
- `src/monitoring/*` → `src/infrastructure/monitoring/`
- `src/observability/*` → `src/infrastructure/observability/`
- `src/storage/*` → `src/infrastructure/database/storage/`
- `src/scrape_state_manager.py` → `src/infrastructure/database/scrape_state_manager.py`

### Application
- `src/api/*` → `src/application/api/`
- `src/core/orchestration/*` → `src/application/orchestration/`
- `src/orchestration/*` → `src/application/orchestration/`
- `src/pipeline/*` → `src/application/automation/`
- `src/main_api.py` → `src/application/api/main_api.py`

### Shared
- `src/utils/*` → `src/shared/utils/`
- `src/core/schemas/*` → `src/shared/schemas/`

## Testing

After restructuring, run the test suite to verify everything works:

```bash
pytest tests/ -v
```

## Verification Checklist

- [x] All files moved to new locations
- [x] All imports updated (359 files updated)
- [x] Backward compatibility files created
- [x] Domain boundaries clear
- [x] No duplicate modules
- [x] No scattered files
- [ ] Tests pass (run `pytest tests/ -v`)
- [ ] Documentation updated

## Next Steps

1. **Remove old directories** (after verification):
   - Keep backward compatibility files for now
   - Remove old directories once all code is verified working

2. **Update documentation**:
   - Update any architecture diagrams
   - Update README files
   - Update developer onboarding docs

3. **Clean up**:
   - Remove backward compatibility files after full migration
   - Update CI/CD scripts if needed
   - Update deployment scripts if needed

## Benefits

1. **Clear Domain Boundaries**: Each business domain is clearly separated
2. **Better Organization**: Related functionality is grouped together
3. **Easier Navigation**: Developers can quickly find code by domain
4. **Scalability**: New features can be added within appropriate domains
5. **Maintainability**: Changes are localized to specific domains

## Questions?

If you encounter any issues with the restructuring, please:
1. Check the backward compatibility files
2. Verify imports are using the new paths
3. Run the test suite
4. Check this migration guide

