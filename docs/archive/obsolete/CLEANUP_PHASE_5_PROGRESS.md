# Phase 5: Configuration Cleanup - In Progress

**Date:** 2025-11-20  
**Status:** In Progress  
**Risk Level:** Low

---

## ✅ Completed: Cookie File Standardization

### Problem
Cookie files were scattered across multiple locations:
- Twitter cookies: `config/twitter_cookies*.json`
- Threads cookies: `cookies/threads_cookies.json` (separate directory)
- Some cookies in root `cookies/` directory
- Inconsistent paths in code

### Solution
**Standardized to:** `config/cookies/` directory

### Changes Made

1. **Created unified directory:**
   - Created `config/cookies/` directory

2. **Moved cookie files:**
   - `cookies/threads_cookies.json` → `config/cookies/threads_cookies.json`
   - `cookies/twitter_cookies_cryptoniard.json` → `config/cookies/twitter_cookies_cryptoniard.json`
   - `cookies/twitter_qronoya_simple.json` → `config/cookies/twitter_qronoya_simple.json`
   - `config/twitter_cookies.json` → `config/cookies/twitter_cookies.json`
   - `config/twitter_cookies_cryptoniard.json` → `config/cookies/twitter_cookies_cryptoniard.json`

3. **Updated code references (8 files):**
   - `src/publishing/platforms/threads_playwright.py` - Updated default path
   - `src/core/extraction/twitter_extractor_playwright.py` - Updated default path
   - `src/publishing/platforms/twitter_playwright.py` - Updated default path
   - `src/core/extraction/twitter/auth_manager.py` - Updated default path
   - `src/api/routes/system.py` - Updated path pattern
   - `scripts/utilities/manage_cookies.py` - Updated both Twitter and Threads paths
   - `scripts/utilities/capture_threads_cookies.py` - Updated default path
   - `scripts/utilities/capture_twitter_cookies.py` - Updated default path

### Result
- ✅ All cookie files in single location: `config/cookies/`
- ✅ All code references updated
- ✅ Consistent path structure
- ✅ Environment variables still work (THREADS_COOKIES_FILE, TWITTER_COOKIE_FILE)

---

## 📋 Remaining Tasks

### 1. Config File Review
- [ ] Audit all config files in `config/`
- [ ] Identify duplicates or redundant configs
- [ ] Consolidate where possible

### 2. Environment Variables Documentation
- [ ] Document all required env vars
- [ ] Create `.env.example` template
- [ ] Verify all are actually used

### 3. Config Structure Review
- [ ] Review `config/personas/` vs `config/profiles/` (potential duplication)
- [ ] Check for unused config files
- [ ] Standardize naming conventions

---

## 📁 Current Cookie Files

All cookie files are now in `config/cookies/`:
- `threads_cookies.json`
- `twitter_cookies.json`
- `twitter_cookies_cryptoniard.json`
- `twitter_qronoya_simple.json`

---

## 🔄 Migration Notes

**Backward Compatibility:**
- Environment variables (`THREADS_COOKIES_FILE`, `TWITTER_COOKIE_FILE`) still work
- If set, they override the default paths
- Old paths will need manual migration if files exist there

**Next Steps:**
1. Test cookie loading with new paths
2. Update any documentation referencing old paths
3. Consider adding migration script for existing deployments

