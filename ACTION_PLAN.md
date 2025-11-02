# PRISMIND - PRIORITIZED ACTION PLAN

## Overview
This document provides a step-by-step action plan to bring PrisMind from 6/10 (critical) to 8.5/10 (production-ready) in 3-4 weeks.

---

## PHASE 1: CRITICAL BLOCKERS (1-2 Days)

### Task 1.1: Fix Broken Test Suite (30 minutes)
**File:** `tests/` directory (5 files)  
**Status:** BLOCKING  

Update imports in these files:
```python
# OLD (DELETED)
from src.supabase_manager import SupabaseManager
from src.services.unified_collection_service import UnifiedCollectionService

# NEW
from src.database.manager import SupabaseManager
from src.services.collection.platform_collectors import collect_twitter_bookmarks
```

**Files to fix:**
1. `tests/test_collection.py` (line 8)
2. `tests/test_integration.py` (line 13)
3. `tests/test_supabase_insert.py` (line 7)
4. `tests/test_supabase_schema.py` (line 12)
5. `tests/test_unified_collection.py` (line 15)

**Verification:**
```bash
pytest tests/test_collection.py -v
pytest tests/test_integration.py -v
pytest tests/test_supabase_insert.py -v
pytest tests/test_supabase_schema.py -v
pytest tests/test_unified_collection.py -v
```

---

### Task 1.2: Remove Socket Patching from Reddit Extractor (1 hour)
**File:** `src/core/extraction/reddit_extractor.py`  
**Status:** SECURITY CRITICAL  

**Current code (lines 76-78):**
```python
# DANGEROUS - Remove this
socket.getaddrinfo = self._patched_getaddrinfo
```

**Action:**
1. Delete lines 65-78 (socket mapping dictionary and patch function)
2. Delete line 77 (socket.getaddrinfo assignment)
3. Replace with HTTPAdapter configuration:

```python
def _create_retry_session(self):
    """Create session with proper retry strategy"""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
```

**Verification:**
```bash
python -c "
from src.core.extraction.reddit_extractor import RedditExtractor
r = RedditExtractor('id', 'secret', 'agent')
print('✓ No socket patching')
"
```

---

### Task 1.3: Apply Supabase Migrations (30 minutes)
**Files:** `migrations/2025_10_31_mimesis.sql`  
**Status:** REQUIRED  

**Action:**
1. Login to Supabase dashboard
2. Go to SQL Editor
3. Copy contents of `migrations/2025_10_31_mimesis.sql`
4. Execute (creates mimesis tables if not present)
5. Verify tables exist:
   - `mimesis_transformations`
   - `scheduled_posts`
   - `posted_content`

---

## PHASE 2: CRITICAL FIXES (3-4 Days)

### Task 2.1: Replace 833 Print Statements with Logging (1 day)
**Scope:** 15+ files  
**Impact:** HIGH  

**Files to fix (priority order):**
1. `src/publishing/platforms/telegram/bot.py` - ~50+ print statements
2. `src/core/extraction/twitter_extractor_playwright.py` - ~76 print statements
3. `src/core/extraction/reddit_extractor.py` - ~40 print statements
4. `src/core/extraction/threads_extractor.py` - ~30 print statements
5. Other service files - ~630 print statements

**Pattern to follow:**
```python
# OLD
print(f"🚀 Starting collection")
print(f"❌ Error: {e}")

# NEW
import logging
logger = logging.getLogger(__name__)

logger.info("Starting collection")
logger.error(f"Error: {e}", exc_info=True)
```

**Use existing logger from:**
`src/utils/logging.py` - provides get_logger() function

**Verification:**
```bash
grep -r "print(" src/ | wc -l  # Should drop from 833 to < 50
```

---

### Task 2.2: Fix Bare Except Clauses (1-2 days)
**Scope:** 20+ files  
**Pattern:** Replace `except:` and broad `except Exception:`

**Files to fix:**
```
src/publishing/platforms/twitter_playwright.py - 3+ bare excepts
src/publishing/platforms/threads_playwright.py - 10+ bare excepts
src/publishing/platforms/telegram/bot.py - multiple
src/research/private_book_library.py - bare except
```

**Pattern to follow:**
```python
# OLD
try:
    something()
except:  # Catches everything including KeyboardInterrupt!
    pass

# NEW
try:
    something()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
except TimeoutError as e:
    logger.warning(f"Timeout: {e}, retrying...")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
```

**Special cases:**
```python
# For functions that should not fail silently:
except (KeyboardInterrupt, SystemExit):
    raise  # Always re-raise these!
```

**Verification:**
```bash
grep -r "except:" src/  # Should be 0
grep -r "except Exception:" src/ | grep -v "as e" | wc -l  # Should be 0
```

---

### Task 2.3: Consolidate Database Managers (2-3 days)
**Current:** 4 different managers creating confusion  
**Target:** 1 canonical manager + optional cache  

**Current state:**
```
src/database/manager.py - SupabaseManager (779 lines)
src/services/new_database_manager.py - NewDatabaseManager
src/storage/supabase_adapter.py - SupabaseAdapter
src/storage/db.py - Storage interface
```

**Plan:**
1. Keep `src/database/manager.py` as primary SupabaseManager
2. Remove/deprecate other facades
3. Create `LocalCache` as simple SQLite wrapper (optional)
4. Update all imports to use single source

**Action steps:**
1. Update `src/storage/db.py` to use SupabaseManager directly
2. Remove wrapper logic from other files
3. Update web app to use single manager:
   ```python
   # Before: Multiple import chains
   # After:
   from src.database.manager import SupabaseManager
   db = SupabaseManager()
   ```

**Verification:**
```bash
grep -r "NewDatabaseManager\|SupabaseAdapter" src/web/ | wc -l  # Should be 0
```

---

## PHASE 3: HIGH PRIORITY IMPROVEMENTS (3-5 Days)

### Task 3.1: Complete Stub Implementations (2-3 days)
**Found:** 93+ stub functions returning empty dicts/None  

**Critical stubs in `src/core/analysis/intelligent_content_analyzer.py`:**

1. **Media Analysis** (currently returns `{}`)
   ```python
   def _analyze_media_content(self, media_urls: List[str]) -> Dict[str, Any]:
       # Currently returns empty dict
       # TODO: Implement with vision APIs
   ```
   - Use Gemini vision API (already configured)
   - Extract text, objects, scene description
   - Cache results

2. **Comment Analysis** (currently returns `[]`)
   ```python
   def _analyze_comments(self, post: SocialPost) -> Dict[str, Any]:
       # Currently returns empty
       # TODO: Sentiment analysis on comments
   ```
   - Aggregate comment sentiment
   - Find most insightful comments
   - Detect discussion quality

3. **Single Media Analysis**
   ```python
   def _analyze_single_media(self, media_url: str) -> Optional[Dict]:
       # Currently returns None
       # TODO: Vision analysis
   ```

**Action:**
- Implement with actual AI calls
- Add caching for performance
- Add error handling

---

### Task 3.2: Split Monolithic Telegram Bot (2-3 days)
**Current:** `src/publishing/platforms/telegram/bot.py` - 2,356 lines (8x too large)

**Split into:**
```
telegram/
├── bot.py              (300 lines - core setup)
├── handlers/
│   ├── command.py      (300 lines)
│   ├── callback.py     (300 lines)
│   └── state.py        (200 lines)
└── formatters.py       (300 lines)
```

**Action:**
1. Extract command handlers to `handlers/command.py`
2. Extract callback handlers to `handlers/callback.py`
3. Extract formatting to `formatters.py`
4. Keep core bot setup in `bot.py`

---

### Task 3.3: Split Oversized Extractors (1-2 days)
**Files to split:**
- `twitter_extractor_playwright.py` (1,583 lines)
- `threads_extractor.py` (1,065 lines)
- `reddit_extractor.py` (941 lines)

**Action:**
- Extract authentication logic
- Extract pagination logic
- Extract post parsing logic
- Keep main extractor class at ~300 lines

---

### Task 3.4: Add Comprehensive Error Handling (1-2 days)
**Scope:** All major functions  

**Pattern:**
```python
async def collect_posts(self) -> List[SocialPost]:
    """Collect posts with proper error handling"""
    try:
        posts = await self._fetch_posts()
        return posts
    except RateLimitError as e:
        logger.warning(f"Rate limited, waiting {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        return await self.collect_posts()  # Retry
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        raise  # Don't hide auth errors
    except NetworkError as e:
        logger.error(f"Network error: {e}, will retry later")
        return []  # Return partial results
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

---

## PHASE 4: TEST COVERAGE (2-3 Days)

### Task 4.1: Add Unit Tests (1-2 days)
**Target:** 80%+ coverage of core logic

**Test files to create/improve:**
1. `tests/unit/test_duplicate_detector.py` - Already exists, expand
2. `tests/unit/test_post_validator.py` - Already exists, expand
3. `tests/unit/test_analysis.py` - Add more cases
4. `tests/unit/test_extractors.py` - Add error cases

**Pattern:**
```python
import pytest
from unittest.mock import Mock, patch

def test_duplicate_detector_url_normalization():
    detector = DuplicateDetector()
    url1 = "https://example.com/post?utm_source=twitter"
    url2 = "https://example.com/post?utm_source=reddit"
    assert detector.normalize_url(url1) == detector.normalize_url(url2)

def test_post_validator_rejects_broken_content():
    validator = PostValidator(strict=True)
    result = validator.validate_post({
        "content": "Extraction failed",
        "author": "unknown",
        "platform": "twitter"
    })
    assert not result.is_valid

@pytest.mark.asyncio
async def test_collection_handles_rate_limit():
    with patch('src.core.extraction.twitter_extractor_playwright.sleep'):
        # Test rate limit handling
        pass
```

---

### Task 4.2: Integration Tests (1 day)
**Target:** Test complete pipelines

```python
@pytest.mark.integration
async def test_full_collection_pipeline():
    """Collect → Analyze → Store → Publish workflow"""
    # Setup
    collector = TwitterExtractorPlaywright(...)
    analyzer = IntelligentContentAnalyzer()
    storage = SupabaseAdapter()
    
    # Collect
    posts = await collector.get_bookmarks()
    assert len(posts) > 0
    
    # Analyze
    for post in posts:
        analysis = analyzer.analyze_bookmark(post)
        assert analysis['value_score'] > 0
    
    # Store
    for post in posts:
        success = storage.save_post(post)
        assert success
```

---

## PHASE 5: TYPE HINTS & DOCUMENTATION (2 Days)

### Task 5.1: Add Type Hints (1 day)
**Target:** 100% function signatures

**Pattern:**
```python
# Before
def analyze_post(self, post):
    return analysis

# After
from typing import Dict, Any, List
from src.core.extraction.social_extractor_base import SocialPost

def analyze_post(self, post: SocialPost) -> Dict[str, Any]:
    """Analyze a post and return analysis results.
    
    Args:
        post: Social media post to analyze
        
    Returns:
        Dictionary with analysis results including value_score,
        sentiment, topics, actionable_insights
        
    Raises:
        ValueError: If post data is invalid
    """
    return analysis
```

---

### Task 5.2: Document Modules (1 day)
**Target:** Module docstring for every Python file  

**Pattern:**
```python
"""
Module: Post Analyzer
====================
Analyzes collected posts using AI and produces quality/value scores.

Key Classes:
  - PostAnalyzer: Main analysis interface

Dependencies:
  - IntelligentContentAnalyzer: AI analysis engine
  - DuplicateDetector: Prevents duplicate analysis

Configuration:
  - SKIP_AI_ANALYSIS env var: Disable AI for performance
  - ANALYSIS_TIMEOUT: Max seconds per post

Example:
    analyzer = PostAnalyzer()
    result = await analyzer.analyze_and_store_post(post_dict, db)
    
See Also:
  - src/core/analysis/intelligent_content_analyzer.py
  - docs/ANALYSIS_PIPELINE.md
"""
```

---

## VERIFICATION CHECKLIST

### After Phase 1:
- [ ] All 5 test suites pass
- [ ] No socket patching in Reddit extractor
- [ ] Supabase migrations applied

### After Phase 2:
- [ ] Less than 50 print statements (from 833)
- [ ] No bare except clauses
- [ ] Single database manager path
- [ ] All tests still passing

### After Phase 3:
- [ ] All monolithic files under 300 lines
- [ ] All stub functions implemented
- [ ] Complete error handling
- [ ] Tests passing at 80%+

### After Phase 4:
- [ ] 80%+ test coverage
- [ ] All critical paths tested
- [ ] Error scenarios covered

### After Phase 5:
- [ ] 100% type hints
- [ ] Module docstrings complete
- [ ] README updated

---

## SUCCESS METRICS

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Health Score | 6/10 | 8.5/10 | 8.5/10 |
| Tests Passing | 70% | 95% | 95% |
| Code Coverage | ~60% | 80%+ | 80%+ |
| Print statements | 833 | <50 | 0 |
| Bare excepts | 20+ | 0 | 0 |
| RULES.md compliance | 48% | 85%+ | 85%+ |
| Max file size | 2,356 | 300 | 300 |
| Type hints | 50% | 95%+ | 100% |
| Security issues | 2 | 0 | 0 |

---

## Timeline

```
Week 1:
  Mon-Tue: Phase 1 (blockers) + Phase 2 (critical) = 40 hours
  
Week 2:
  Phase 3 (improvements) + Phase 4 (tests) = 40 hours
  
Week 3:
  Phase 5 (polish) + verification = 30 hours
  
Week 4:
  Performance optimization + final QA = 20 hours

Total: 130 hours (3.3 weeks)
```

---

## Quick Win Opportunities

These can be done in parallel to save time:

1. **30 min:** Fix test imports (can run tests while doing other work)
2. **1 hour:** Remove socket patching
3. **Parallel:** While fixing logging in files A, teammate can fix error handling in files B

---

## Questions to Ask

Before starting, clarify:

1. Priority: Are performance optimizations or test coverage more important?
2. Timeline: Can we extend to 4 weeks if needed?
3. Resources: Single person or team?
4. Backward compatibility: Do we need to support old code paths?
5. Rollout: Gradual migration or big bang?

---

**Status:** Ready to execute  
**Last Updated:** November 1, 2025  
**Owner:** Development Team

