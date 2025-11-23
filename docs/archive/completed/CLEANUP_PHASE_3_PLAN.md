# Cleanup Phase 3: Code Quality Improvements

**Status:** Ready to execute  
**Risk Level:** Low  
**Impact:** High (improves maintainability, reduces confusion)

---

## Overview

Focus on quick wins that improve code quality without major refactoring:
1. Remove unused imports
2. Fix import inconsistencies
3. Standardize import ordering
4. Remove dead code

---

## Phase 3.1: Unused Imports Cleanup

### Tools to Use
- `autoflake` - removes unused imports and variables
- `isort` - sorts imports consistently
- Manual review for edge cases

### Approach
1. Run `autoflake` on entire codebase
2. Review changes (some may be false positives)
3. Run `isort` to standardize import ordering
4. Test to ensure nothing breaks

### Files to Check First
- Files with many imports (from grep results):
  - `src/api/main.py` (22 imports)
  - `src/api/routes/persona_studio.py` (18 imports)
  - `src/publishing/platforms/telegram/bot.py` (25 imports)
  - `src/pipeline/full_automation_loop.py` (15 imports)

---

## Phase 3.2: Import Inconsistencies

### Issues to Fix
1. **Mixed import styles:**
   - Some files use `from src.database.manager import SupabaseManager`
   - Others use `from src.database import SupabaseManager`
   - Standardize to one style

2. **Relative vs absolute imports:**
   - Some use relative: `from ..database import`
   - Others use absolute: `from src.database import`
   - Standardize to absolute imports (better for clarity)

3. **Import grouping:**
   - Standard library
   - Third-party
   - Local imports
   - Use `isort` profile

---

## Phase 3.3: Dead Code Removal

### What to Look For
1. **Unused functions/classes:**
   - Functions never called
   - Classes never instantiated
   - Methods never used

2. **Commented-out code:**
   - Large blocks of commented code
   - Old implementations left in place

3. **Unreachable code:**
   - Code after `return` statements
   - Code in `if False:` blocks

### Tools
- `vulture` - finds dead code
- Manual review (tools can have false positives)

---

## Phase 3.4: Large Files Analysis

### Files Over 2000 Lines
1. `src/core/extraction/twitter_extractor_playwright.py` - 4746 lines
2. `src/core/extraction/threads_extractor.py` - 3458 lines
3. `src/publishing/rewriter.py` - 3187 lines (deprecated, will be removed)
4. `src/core/analysis/intelligent_content_analyzer.py` - 2804 lines
5. `src/publishing/platforms/telegram/bot.py` - 2394 lines

### Action Plan
- **Document** what each large file does
- **Identify** logical boundaries for future splitting
- **Don't split yet** - just document for Phase 4

---

## Execution Order

1. ✅ **Phase 3.1:** Unused imports (autoflake + isort)
2. ✅ **Phase 3.2:** Import standardization
3. ✅ **Phase 3.3:** Dead code identification (document, don't delete yet)
4. ✅ **Phase 3.4:** Large files documentation

---

## Success Criteria

- [ ] All unused imports removed
- [ ] Import style consistent across codebase
- [ ] Import ordering standardized
- [ ] Dead code identified and documented
- [ ] Large files analyzed and documented
- [ ] All tests still pass
- [ ] No functionality broken

---

## Notes

- **Conservative approach:** Don't delete dead code yet, just document it
- **Test after each step:** Ensure nothing breaks
- **Use tools but verify:** Auto-tools can have false positives






