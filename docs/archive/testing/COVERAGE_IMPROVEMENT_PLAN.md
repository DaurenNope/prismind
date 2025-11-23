# Coverage Improvement Plan

## Current Status

**Baseline Coverage**: 11% overall
**Target Coverage**: 80%+
**Gap**: 69% to reach target

---

## Priority-Based Improvement Plan

### Phase 1: Critical Paths (P0) - Target: 80%+

#### Storage Layer (`src/storage/`) - Current: 42%
**Target**: 80%+

**Tests Needed**:
- ✅ Storage facade operations (partial)
- ⏳ Supabase adapter (37% → 80%)
- ⏳ SQLite adapter (29% → 80%)
- ⏳ ID generator (27% → 80%)
- ⏳ Sync operations
- ⏳ Error handling

**Estimated Tests**: 20-30 additional tests

#### Database Layer (`src/database/`) - Current: ~50%
**Target**: 80%+

**Tests Needed**:
- ✅ Database agent (partial)
- ⏳ Database operations
- ⏳ Query operations
- ⏳ Transaction handling
- ⏳ Error recovery

**Estimated Tests**: 15-20 additional tests

---

### Phase 2: Core Functionality (P1) - Target: 70%+

#### Collectors (`src/services/collection/`) - Current: 22%
**Target**: 70%+

**Tests Needed**:
- ✅ Basic collector tests (partial)
- ⏳ Twitter collector edge cases
- ⏳ Reddit collector edge cases
- ⏳ Threads collector edge cases
- ⏳ Error handling
- ⏳ Duplicate detection
- ⏳ Rate limiting

**Estimated Tests**: 30-40 additional tests

#### Analyzers (`src/services/analysis/`) - Current: 27%
**Target**: 70%+

**Tests Needed**:
- ✅ Basic analyzer tests (partial)
- ⏳ AI service integration
- ⏳ Content parsing
- ⏳ Analysis pipeline
- ⏳ Error handling
- ⏳ Rate limiting

**Estimated Tests**: 25-35 additional tests

#### Publishing (`src/publishing/`) - Current: ~5%
**Target**: 70%+

**Tests Needed**:
- ✅ Rewriter components (partial)
- ✅ Persona matcher (64% → 80%)
- ✅ Persona manager (partial)
- ✅ RAG system (partial)
- ⏳ Publishing worker
- ⏳ Voice validator
- ⏳ Thread splitter
- ⏳ Engagement learner

**Estimated Tests**: 40-50 additional tests

---

### Phase 3: Extended Coverage (P2) - Target: 60%+

#### Research Agents (`src/agents/`) - Current: ~10%
**Target**: 60%+

**Tests Needed**:
- ⏳ GitHub research agent
- ⏳ Book research agent
- ⏳ Discovery agents
- ⏳ Error handling

**Estimated Tests**: 20-30 additional tests

#### Bot Commands (`src/services/telegram_*`) - Current: 0%
**Target**: 60%+

**Tests Needed**:
- ⏳ Telegram bot commands
- ⏳ Command handlers
- ⏳ Error responses
- ⏳ Collection commands

**Estimated Tests**: 15-20 additional tests

#### Utilities (`src/utils/`) - Current: ~50%
**Target**: 70%+

**Tests Needed**:
- ⏳ Duplicate detector (36% → 70%)
- ⏳ Post validator (60% → 80%)
- ⏳ Observability hub (52% → 70%)
- ⏳ Config utilities (87% - maintain)

**Estimated Tests**: 20-25 additional tests

---

## Implementation Strategy

### Week 1: Critical Paths
1. Complete storage layer tests (80%+)
2. Complete database layer tests (80%+)
3. Add transaction tests
4. Add error recovery tests

**Expected Coverage**: 25-30%

### Week 2: Core Functionality
1. Complete collector tests (70%+)
2. Complete analyzer tests (70%+)
3. Expand publishing tests (70%+)

**Expected Coverage**: 50-60%

### Week 3: Extended Coverage
1. Research agent tests (60%+)
2. Bot command tests (60%+)
3. Utility tests (70%+)

**Expected Coverage**: 70-75%

### Week 4: Polish & Edge Cases
1. Edge case tests
2. Error condition tests
3. Performance tests
4. Coverage review

**Expected Coverage**: 80%+

---

## Test Categories

### Unit Tests (Fast, Isolated)
- Mock all external dependencies
- Test single components
- Fast execution (< 100ms per test)
- High coverage target (80%+)

### Integration Tests (Component Interaction)
- Test component interactions
- Mock external services
- Medium execution time
- Moderate coverage target (70%+)

### E2E Tests (Full System)
- Test complete workflows
- May require test infrastructure
- Slower execution
- Lower coverage target (50%+)

---

## Coverage Tracking

### Metrics to Track
- Overall coverage percentage
- Coverage by module
- Coverage by test type
- Coverage trends over time

### Reporting
- Coverage report in CI
- Coverage trends in PRs
- Coverage dashboard (if available)

---

## Success Criteria

### Phase 1 (Critical Paths)
- ✅ Storage layer: 80%+
- ✅ Database layer: 80%+
- ✅ Overall: 25-30%

### Phase 2 (Core Functionality)
- ✅ Collectors: 70%+
- ✅ Analyzers: 70%+
- ✅ Publishing: 70%+
- ✅ Overall: 50-60%

### Phase 3 (Extended Coverage)
- ✅ Research agents: 60%+
- ✅ Bot commands: 60%+
- ✅ Utilities: 70%+
- ✅ Overall: 70-75%

### Final (Polish)
- ✅ Overall: 80%+
- ✅ Critical paths: 90%+
- ✅ All tests passing
- ✅ CI integration complete

---

## Notes

- Coverage baseline: 11%
- Target coverage: 80%+
- Estimated total tests needed: 200-300 additional tests
- Focus on critical paths first
- Maintain test quality while increasing coverage

---

**Last Updated**: Initial plan created
**Next Review**: After Phase 1 completion






