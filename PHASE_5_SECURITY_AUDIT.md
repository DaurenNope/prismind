# 🔴 PHASE 5: SECURITY AUDIT & REMEDIATION

## Status: IN PROGRESS

---

## 1. 🔐 SECURITY ISSUES

### Critical: .env File Management
**Status**: NEEDS IMMEDIATE ACTION

**Tasks**:
- [ ] Check if .env is in git history
- [ ] If committed, remove from history using `git filter-branch` or BFG
- [ ] Rotate ALL exposed keys:
  - [ ] Reddit API keys
  - [ ] Telegram bot token
  - [ ] Supabase URL & keys
  - [ ] Twitter credentials
  - [ ] Any other API keys
- [ ] Ensure .env is in .gitignore
- [ ] Update .env.example with template (no real values)
- [ ] Document key rotation in security log

### Medium: Session & Log Files
**Status**: NEEDS CLEANUP

**Files to remove from git history**:
- [ ] `*.log` files
- [ ] `*.pid` files  
- [ ] `telegram_scraper.session`
- [ ] Any other session artifacts

**Tasks**:
- [ ] Update .gitignore to include:
  ```
  *.log
  *.pid
  *.session
  telegram_scrape.log
  telegram_scrape.pid
  ```
- [ ] Remove tracked files: `git rm --cached <files>`
- [ ] Commit updated .gitignore

### Medium: Supabase Service Role Key Audit
**Status**: NEEDS REVIEW

**Tasks**:
- [ ] Audit all files using `SUPABASE_SERVICE_ROLE_KEY`
- [ ] Ensure it's only used in:
  - Backend services (src/services/)
  - Collection scripts (run_full_collection.py)
  - NOT in frontend/UI code
- [ ] Consider creating restricted keys for different use cases

---

## 2. 📦 DEPENDENCIES CLEANUP

### requirements.txt Issues
**Status**: NEEDS AUDIT

**Tasks**:
- [ ] Check for duplicate packages
- [ ] Remove unused dependencies:
  - [ ] Check if `selenium` is actually used
  - [ ] Check for other unused packages
- [ ] Verify all needed packages present:
  - [x] feedparser ✅
  - [x] apscheduler ✅
  - [ ] httpx
  - [ ] telethon
  - [ ] psutil
  - [ ] sgmllib3k
- [ ] Fix any version conflicts
- [ ] Document Playwright setup requirement

### Playwright Documentation
**Status**: NEEDS UPDATE

**Tasks**:
- [ ] Add to README.md:
  ```bash
  # After pip install -r requirements.txt
  python -m playwright install
  ```
- [ ] Add to setup documentation
- [ ] Note browser requirements (Chromium)

---

## 3. 🧪 TESTING INFRASTRUCTURE

### Fix test_all_systems.py
**Status**: NEEDS FIX

**Issues**:
- Absolute path hacks with `sys.path.insert()`
- Tests may not run from project root

**Tasks**:
- [ ] Remove `sys.path.insert()` hacks
- [ ] Use relative imports or proper package structure
- [ ] Ensure tests run with: `pytest tests/`
- [ ] Add pytest configuration if needed

### Add Automated Tests
**Status**: MISSING

**Required Tests**:
- [ ] **Discovery Pipeline Test**:
  - Test RSS collection → Supabase → UI flow
  - Test deduplication
  - Test quality filtering
  
- [ ] **Collector Tests**:
  - Test Twitter extractor
  - Test Reddit extractor
  - Test Threads extractor
  - Test schema compliance
  
- [ ] **Database Tests**:
  - Test SQLite operations
  - Test Supabase sync
  - Test duplicate detection
  
- [ ] **UI Tests**:
  - Test dashboard loads
  - Test feed rendering
  - Test dismiss functionality

---

## 4. 📚 DOCUMENTATION SYNC

### README.md Update
**Status**: NEEDS SYNC

**Tasks**:
- [ ] Update system overview to match Phase 4
- [ ] Document autonomous discovery system
- [ ] Document 60 edgy RSS sources
- [ ] Update setup instructions
- [ ] Add Phase 5 status
- [ ] Remove outdated information

### Setup Documentation
**Tasks**:
- [ ] Document Playwright installation
- [ ] Document Supabase setup
- [ ] Document .env configuration
- [ ] Add troubleshooting section

---

## 5. 🔍 CODE QUALITY CHECKS

### Remove Dead References
**Status**: NEEDS CLEANUP

**Tasks**:
- [ ] Remove references to `new_app.py`
- [ ] Remove references to deleted scripts
- [ ] Clean up unused imports
- [ ] Remove commented-out code

### Verify Data Contracts
**Status**: NEEDS VERIFICATION

**Tasks**:
- [ ] Audit `SocialPost` usage in all collectors
- [ ] Verify all collectors provide required fields
- [ ] Check for schema mismatches
- [ ] Test with real data

### Storage Layer Audit
**Status**: NEEDS VERIFICATION

**Tasks**:
- [ ] Verify `DatabaseOperations.add_post()` only writes to SQLite
- [ ] Confirm Supabase sync is separate
- [ ] Check score normalization (0-10 scale)
- [ ] Verify deduplication logic

---

## 6. ⚡ PERFORMANCE & RELIABILITY

### Error Handling
**Tasks**:
- [ ] Add comprehensive error handling to collectors
- [ ] Add retry logic for network failures
- [ ] Add graceful degradation
- [ ] Log errors properly

### Monitoring
**Tasks**:
- [ ] Add health check endpoint
- [ ] Add collection success/failure tracking
- [ ] Add performance metrics
- [ ] Set up alerting (optional)

---

## PRIORITY ORDER

1. 🔴 **CRITICAL**: Security (#1) - .env cleanup and key rotation
2. 🟡 **HIGH**: Dependencies (#2) - Clean requirements.txt
3. 🟡 **HIGH**: Testing (#3) - Add automated tests
4. 🟢 **MEDIUM**: Documentation (#4) - Sync README
5. 🟢 **MEDIUM**: Code Quality (#5) - Cleanup and verification
6. 🟢 **LOW**: Performance (#6) - Monitoring and optimization

---

## COMPLETION CRITERIA

Phase 5 is complete when:
- ✅ No secrets in git history
- ✅ All keys rotated and secure
- ✅ requirements.txt is clean and documented
- ✅ Automated tests cover critical paths
- ✅ README matches current system
- ✅ All remediation checklist items addressed
- ✅ System is production-ready

---

## NEXT ACTIONS

**Immediate (Today)**:
1. Check git history for .env
2. Audit requirements.txt
3. Create security cleanup plan

**Short-term (This Week)**:
1. Rotate exposed keys
2. Clean up dependencies
3. Add critical tests
4. Update README

**Medium-term (Next Week)**:
1. Complete test suite
2. Code quality cleanup
3. Performance optimization
4. Final production readiness check
