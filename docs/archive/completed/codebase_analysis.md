# Codebase Structure Analysis Report

**Total Python files**: 275

## Duplicate Modules

### agents
- `src/publishing/platforms/telegram/agents.py`
- `src/api/routes/agents.py`

### analysis
- `src/database/analysis.py`
- `src/api/routes/analysis.py`

### auth
- `src/core/extraction/twitter/auth.py`
- `src/api/auth.py`

### circuit_breaker
- `src/publishing/circuit_breaker.py`
- `src/resilience/circuit_breaker.py`

### config
- `src/agents/config.py`
- `src/utils/config.py`

### health
- `src/database/health.py`
- `src/api/routes/health.py`
- `src/services/health.py`

### interaction_client
- `src/twitter/interaction_client.py`
- `src/threads/interaction_client.py`

### metrics
- `src/database/metrics.py`
- `src/monitoring/metrics.py`

### orchestrator
- `src/publishing/modular_rewriter/orchestrator.py`
- `src/pipeline/orchestrator.py`

### persona_matcher
- `src/publishing/persona_matcher.py`
- `src/services/persona_matcher.py`

### semantic_search
- `src/research/semantic_search.py`
- `src/core/research/semantic_search.py`

## Scattered Files

### root_level
- `/Users/mac/Documents/Development/prismind/src/scrape_state_manager.py`
- `/Users/mac/Documents/Development/prismind/src/main_api.py`

### services_directory
- `/Users/mac/Documents/Development/prismind/src/services/cancel_manager.py`
- `/Users/mac/Documents/Development/prismind/src/services/digest.py`
- `/Users/mac/Documents/Development/prismind/src/services/profile_publishing_orchestrator.py`
- `/Users/mac/Documents/Development/prismind/src/services/profile_content_selector.py`
- `/Users/mac/Documents/Development/prismind/src/services/discovery.py`
- `/Users/mac/Documents/Development/prismind/src/services/health.py`
- `/Users/mac/Documents/Development/prismind/src/services/profile_wizard.py`
- `/Users/mac/Documents/Development/prismind/src/services/automation.py`
- `/Users/mac/Documents/Development/prismind/src/services/telegram_collection_commands.py`
- `/Users/mac/Documents/Development/prismind/src/services/notifier_webhook.py`
- `/Users/mac/Documents/Development/prismind/src/services/persona_matcher.py`
- `/Users/mac/Documents/Development/prismind/src/services/analysis_lock.py`
- `/Users/mac/Documents/Development/prismind/src/services/new_database_manager.py`
- `/Users/mac/Documents/Development/prismind/src/services/performance_poller.py`
- `/Users/mac/Documents/Development/prismind/src/services/posting_service.py`
- `/Users/mac/Documents/Development/prismind/src/services/rewrite_angle_suggester.py`
- `/Users/mac/Documents/Development/prismind/src/services/unified_collection_service.py`
- `/Users/mac/Documents/Development/prismind/src/services/summarizer.py`
- `/Users/mac/Documents/Development/prismind/src/services/profile_content_pipeline.py`
- `/Users/mac/Documents/Development/prismind/src/services/analysis_runner.py`

## Directory Structure

- `.`: 2 files
- `agents`: 12 files
- `agents/specialized`: 6 files
- `api`: 4 files
- `api/routes`: 13 files
- `core`: 1 files
- `core/analysis`: 18 files
- `core/collection`: 2 files
- `core/discovery`: 9 files
- `core/extraction`: 12 files
- `core/extraction/twitter`: 10 files
- `core/indexing`: 4 files
- `core/learning`: 4 files
- `core/memory`: 1 files
- `core/normalization`: 2 files
- `core/orchestration`: 3 files
- `core/rate_limiting`: 4 files
- `core/research`: 16 files
- `core/schemas`: 2 files
- `core/validation`: 3 files
- `database`: 17 files
- `database/publishing`: 2 files
- `gateway`: 1 files
- `intelligence`: 2 files
- `messaging`: 1 files
- `monitoring`: 5 files
- `observability`: 1 files
- `orchestration`: 1 files
- `pipeline`: 3 files
- `publishing`: 24 files
- `publishing/modular_rewriter`: 13 files
- `publishing/platforms`: 5 files
- `publishing/platforms/telegram`: 4 files
- `publishing/services`: 2 files
- `research`: 7 files
- `resilience`: 2 files
- `services`: 21 files
- `services/analysis`: 1 files
- `services/collection`: 2 files
- `services/supabase`: 1 files
- `social`: 2 files
- `storage`: 4 files
- `threads`: 1 files
- `threadscom`: 1 files
- `twitter`: 2 files
- `utils`: 22 files
