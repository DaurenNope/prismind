# Pending Configuration Tasks

**Date**: 2025-01-11  
**Status**: Documentation Complete, Actions Required

## Overview

This document outlines pending configuration tasks that require manual intervention or review.

## Critical Tasks

### 1. Threads Authentication Configuration ⚠️

**Status**: Blocked - Cookie file missing  
**Priority**: P1 - High  
**Impact**: Threads collection is disabled

**Current Status**:
- Authentication fails: `❌ Failed - no cookie file`
- Collection blocked until cookies configured
- Error: "Could not log you in now. Please try again later."

**Setup Required**:

#### Option 1: Cookie File (Recommended)

1. **Capture Cookies**:
   ```bash
   # Use cookie capture script
   python scripts/utilities/capture_threads_cookies.py
   ```

2. **Manual Cookie Export**:
   - Open Chrome/Edge
   - Go to https://www.threads.net and log in
   - Install "EditThisCookie" extension
   - Export cookies as JSON
   - Save to `config/cookies/threads_cookies.json`

3. **Environment Variable** (Optional):
   ```bash
   THREADS_COOKIES_FILE=config/cookies/threads_cookies.json
   ```

#### Option 2: Username/Password

1. **Set Environment Variables**:
   ```bash
   THREADS_USERNAME=your_username
   THREADS_PASSWORD=your_password
   ```

2. **Note**: Password auth opens visible browser (not headless)

**Verification**:
```bash
# Test authentication
python -c "
from src.core.extraction.threads.threads_extractor import ThreadsExtractor
import asyncio
async def test():
    extractor = ThreadsExtractor()
    result = await extractor.authenticate()
    print(f'Authentication: {\"✅ Success\" if result else \"❌ Failed\"}')
asyncio.run(test())
"
```

**Files**:
- `config/cookies/threads_cookies.json` - Cookie file location
- `scripts/utilities/capture_threads_cookies.py` - Cookie capture script
- `src/publishing/platforms/threads_playwright.py` - Posting (uses same auth)

**Status**: ⚠️ Pending Manual Configuration

### 2. Twitter Thread Extraction Review ⚠️

**Status**: Intentionally Disabled - Pending Review  
**Priority**: P2 - Medium  
**Impact**: Missing thread content, but collection works

**Current Status**:
- Thread detection: ✅ Working
- Thread extraction: ⚠️ Disabled (intentional)
- Reason: DOM workaround to avoid navigation issues

**Location**: `src/core/extraction/twitter/twitter_extractor_*.py`

**Current Behavior**:
```python
if has_thread_indicator:
    # Thread detected but skipping extraction to avoid DOM issues
    main_tweet.post_type = 'thread'
    # Extraction disabled
```

**Options**:

#### Option A: Enable Thread Extraction

1. **Review Implementation**:
   - Check `src/core/extraction/twitter/` for thread extraction code
   - Review ThreadHandler implementation
   - Test with real threads

2. **Enable in Config**:
   ```json
   {
     "twitter": {
       "extract_threads": true
     }
   }
   ```

3. **Test**:
   ```bash
   # Run collection with thread extraction
   python scripts/collection/run_full_collection.py
   ```

#### Option B: Keep Disabled

- Current approach: Collect main tweet, mark as thread
- Less data but more stable
- Avoids DOM navigation issues

**Action Required**: Manual review and decision

**Status**: ⚠️ Pending Review

## Verification Steps

### Verify Threads Authentication

```bash
# Check cookie file exists
ls -la config/cookies/threads_cookies.json

# Check cookie count (should be 10+ cookies)
python -c "
import json
with open('config/cookies/threads_cookies.json') as f:
    cookies = json.load(f).get('cookies', [])
print(f'Cookies: {len(cookies)} (expected: 10+)')
"
```

### Verify Twitter Thread Extraction

```bash
# Check config
cat config/collection.json | grep extract_threads

# Review implementation
grep -n "thread" src/core/extraction/twitter/*.py | grep -i extract
```

## Documentation References

- **Threads Auth**: `docs/archive/THREADS_AUTH_ISSUE.md`
- **Collection Status**: `docs/COMPREHENSIVE_STATUS_REPORT.md`
- **Cookie Scripts**: `scripts/utilities/capture_threads_cookies.py`

## Summary

| Task | Status | Priority | Action Required |
|------|--------|----------|----------------|
| Threads Authentication | ⚠️ Blocked | P1 | Configure cookie file |
| Twitter Thread Extraction | ⚠️ Disabled | P2 | Review and enable if stable |

**Next Steps**:
1. Configure Threads authentication (capture cookies)
2. Review Twitter thread extraction implementation
3. Enable thread extraction if stable
4. Test both features
5. Document results






