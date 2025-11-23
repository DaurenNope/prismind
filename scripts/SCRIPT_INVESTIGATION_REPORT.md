# Script Investigation Report
## Understanding What Each Script Does and Why It Exists

**Date:** 2025-11-20  
**Purpose:** Map out all scripts, their actual functionality, dependencies, and usage patterns

---

## 📊 Summary Statistics

- **Total Active Scripts:** 76
- **Total Archived Scripts:** 56
- **Reduction:** 130+ → 76 (41% reduction)

---

## 🔍 Analysis Directory (3 scripts)

### 1. `analyze_unanalyzed_posts.py`
**Purpose:** Batch analyze posts that haven't been analyzed yet  
**What it does:**
- Fetches posts from `NewDatabaseManager` that have no analysis
- Calls `analyze_and_store_post()` for each unanalyzed post
- Syncs to Supabase if available
- Provides progress tracking and error reporting

**Why it exists:** Core functionality - needed to process new collected posts  
**Dependencies:** `NewDatabaseManager`, `analyze_and_store_post`, `SupabaseManager`  
**Usage:** Run when new posts are collected but not yet analyzed

---

### 2. `fast_recategorize.py`
**Purpose:** Fast rule-based recategorization using keyword matching  
**What it does:**
- Uses `SimpleCategorizer` (keyword-based, not AI)
- Recategorizes posts in Supabase
- Only updates if category changed or was generic
- Much faster than AI-based categorization

**Why it exists:** Performance optimization - AI categorization is slow, this is instant  
**Dependencies:** `SupabaseManager`, `SimpleCategorizer`  
**Usage:** Run when categories need bulk fixing (e.g., after analysis changes)

**Note:** This is DIFFERENT from AI-based recategorization - it's a fast fallback

---

### 3. `production_content_pipeline.py`
**Purpose:** Complete production pipeline - from usable_posts to scheduled publishing  
**What it does:**
1. Gets best content from `usable_posts` (time-sensitive first, then evergreen)
2. Rewrites content with persona voice using `ContentRewriter`
3. Schedules posts for specific times
4. Publishes to Threads/Telegram

**Why it exists:** End-to-end production workflow  
**Dependencies:** `ContentRewriter`, `ProfileContentPipeline`, Supabase  
**Usage:** Run daily to generate posting schedule

**Note:** Uses DEPRECATED `ContentRewriter` - should migrate to `ModularRewriter`

---

## 🗄️ Database Directory (18 scripts)

### Validation Scripts (3 scripts)

#### `validate_usable_posts.py`
**Purpose:** Validate that posts in `usable_posts` meet strict curation criteria  
**What it checks:**
- Content quality (length, truncation, suspicious patterns)
- Time-sensitive keywords in evergreen posts
- Age validation (evergreen >=7 days, time-sensitive <=7 days)
- Score validation (rewrite_score, value_score, quality_score > 0)
- Category validation (not DEPRECATED, NEWS can't be evergreen)
- Analysis model validation
- AI summary validation
- Urgency score validation for evergreen

**Why it exists:** Quality assurance - ensures 100% usable content  
**Usage:** Run after curation to verify quality

---

#### `validate_all_posts.py`
**Purpose:** Run quality validation on ALL posts (not just usable)  
**What it does:**
- Uses `PostValidator` with strict mode
- Validates all posts from `NewDatabaseManager`
- Reports quality metrics (valid, low-quality, invalid)
- Can filter by platform

**Why it exists:** Broader validation - checks entire database quality  
**Usage:** Run periodically to check overall database health

**Difference from `validate_usable_posts.py`:**
- `validate_usable_posts.py`: Only checks posts that SHOULD be usable (strict criteria)
- `validate_all_posts.py`: Checks ALL posts (broader quality check)

---

#### `validate_evergreen_posts.py`
**Purpose:** Validate that posts marked "evergreen" are actually evergreen  
**What it does:**
- Analyzes if evergreen posts contain time-sensitive keywords
- Identifies posts that should be in `usable_posts` table
- Checks age boundaries (7 days minimum, 6 months maximum)
- Reports false positives (time-sensitive marked as evergreen)

**Why it exists:** Specific validation for evergreen classification accuracy  
**Usage:** Run when evergreen classification seems off

---

### Check Scripts (4 scripts - DIFFERENT PURPOSES)

#### `check_by_insertion_time.py`
**Purpose:** Diagnostic script - check specific posts by database insertion order  
**What it does:**
- Shows most recent posts by database ID (auto-increment)
- Checks specific hardcoded post IDs
- Used for debugging specific collection issues

**Why it exists:** One-time diagnostic tool for specific debugging  
**Usage:** Run when investigating specific post collection issues

**Note:** This is a SPECIFIC diagnostic, not a general tool

---

#### `check_circuit_breaker_status.py`
**Purpose:** Check API circuit breaker status (rate limiting protection)  
**What it does:**
- Displays global circuit breaker state (open/closed)
- Shows provider status (OpenAI, Anthropic, etc.)
- Reports failure counts, exhausted keys
- Provides recommendations

**Why it exists:** Monitoring tool for API health  
**Usage:** Run when API calls are failing or rate-limited

**Note:** Completely different purpose from other "check" scripts

---

#### `check_sync_status.py`
**Purpose:** Check sync status between SQLite and Supabase  
**What it does:**
- Reports total posts in SQLite
- Shows how many are synced to Supabase
- Lists unsynced posts with errors
- Provides health report

**Why it exists:** Monitor database synchronization health  
**Usage:** Run to check if local and remote databases are in sync

---

#### `check_truncation.py`
**Purpose:** Check if posts are truncated (incomplete content)  
**What it does:**
- Analyzes latest posts for truncation signs:
  - Ends with ellipsis (...)
  - Ends mid-sentence
  - Ends with comma
  - Contains "show more"
  - Incomplete sentences
- Reports truncation rate

**Why it exists:** Quality check - truncated posts are unusable  
**Usage:** Run after collection to verify content completeness

---

### Comprehensive Validation

#### `comprehensive_validation.py`
**Purpose:** Comprehensive validation with ALL edge cases  
**What it checks:**
- All checks from `validate_usable_posts.py` PLUS:
- Suspicious patterns (test/placeholder language, deleted content)
- Truncation markers
- Placeholder AI summaries
- Boundary conditions (exactly 7 days, exactly 6 months)

**Why it exists:** Most thorough validation - catches everything  
**Usage:** Run for final quality check before production

**Note:** This is the MOST comprehensive - includes all edge cases

---

### Cleanup Scripts (5 scripts - DIFFERENT PURPOSES)

#### `cleanup_bad_posts.py`
**Purpose:** Remove posts with multiple quality issues  
**What it does:**
- Uses `DatabaseAgent.cleanup_bad_posts()`
- Identifies posts with 2+ issues (truncation, low quality, etc.)
- Dry-run mode available
- Deletes from both SQLite and Supabase

**Why it exists:** Remove low-quality content from database  
**Usage:** Run periodically to clean up bad data

---

#### `cleanup_stale_usable_posts.py`
**Purpose:** Remove time-sensitive posts that are past their relevance window  
**What it does:**
- Removes `same-day` posts > 24 hours old
- Removes `24-72h` posts > 72 hours old
- Removes `this-week` posts > 7 days old
- KEEPS evergreen posts (always valid)

**Why it exists:** Keep `usable_posts` table clean - only current content  
**Usage:** Run daily/weekly to remove expired time-sensitive posts

---

#### `cleanup_supabase.py`
**Purpose:** Clean up messed up Supabase data and resync from local  
**What it does:**
- Cleans and validates post data
- Removes None values and empty strings
- Resyncs from local SQLite to Supabase
- Handles data format inconsistencies

**Why it exists:** Fix data corruption/format issues in Supabase  
**Usage:** Run when Supabase data is corrupted or inconsistent

---

#### `clean_supabase_safe.py`
**Purpose:** Safe cleanup of Supabase (less aggressive)  
**What it does:**
- Similar to `cleanup_supabase.py` but safer
- More conservative cleanup rules
- Less likely to delete valid data

**Why it exists:** Safer alternative to `cleanup_supabase.py`  
**Usage:** Run when you want cleanup but are worried about data loss

**Note:** These two cleanup scripts might be redundant - need to compare

---

### Delete Scripts (3 scripts)

#### `delete_posts.py`
**Purpose:** Delete posts by various criteria (comprehensive tool)  
**What it does:**
- Delete by post IDs
- Delete by platform
- Delete by author
- Delete by content substring
- Delete by timestamp
- Dry-run mode
- Deletes from both SQLite and Supabase

**Why it exists:** Flexible deletion tool for various use cases  
**Usage:** Run when you need to delete specific posts

---

#### `delete_recent_twitter_posts.py`
**Purpose:** Delete recent Twitter posts (specific use case)  
**What it does:**
- Deletes Twitter posts collected after a specific timestamp
- More specific than `delete_posts.py`

**Why it exists:** Specific use case - might be redundant with `delete_posts.py`  
**Usage:** Run to remove recent Twitter posts

**Note:** Could potentially be replaced by `delete_posts.py --platform twitter --since <timestamp>`

---

#### `remove_stray_twitter_posts.py`
**Purpose:** Remove stray/duplicate Twitter posts  
**What it does:**
- Identifies duplicate or stray posts
- Removes them from database

**Why it exists:** Specific cleanup for duplicate posts  
**Usage:** Run when duplicates are detected

**Note:** Might overlap with `delete_posts.py` functionality

---

### Other Database Scripts

#### `mark_truncated_posts.py`
**Purpose:** Mark posts as truncated in database  
**What it does:**
- Identifies truncated posts
- Updates database flag
- Doesn't delete, just marks

**Why it exists:** Flag truncated posts without deleting  
**Usage:** Run to mark truncated posts for later review

---

#### `sync_sqlite_to_supabase.py`
**Purpose:** Sync all SQLite posts to Supabase  
**What it does:**
- Gets all posts from SQLite
- Syncs to Supabase
- Handles errors and retries

**Why it exists:** Manual sync when auto-sync fails  
**Usage:** Run when databases are out of sync

---

#### `retry_failed_syncs.py`
**Purpose:** Retry posts that failed to sync  
**What it does:**
- Gets posts with sync errors
- Retries syncing them
- Reports success/failure

**Why it exists:** Recover from transient sync failures  
**Usage:** Run after fixing sync issues

---

## 🍪 Utilities Directory (26 scripts)

### Cookie Management (5 scripts)

#### `manage_cookies.py`
**Purpose:** Comprehensive cookie management tool  
**What it does:**
- Check cookie file status
- Validate cookies
- Test cookie authentication
- Works for both Twitter and Threads

**Why it exists:** Main cookie management interface  
**Usage:** Run to check/validate cookies

---

#### `capture_threads_cookies.py`
**Purpose:** Capture Threads cookies using Playwright  
**What it does:**
- Opens Instagram login (Threads uses Instagram auth)
- Waits for user to log in
- Captures cookies
- Saves to file

**Why it exists:** Automated cookie capture for Threads  
**Usage:** Run when Threads cookies expire

**Note:** This is a CAPTURE tool, `manage_cookies.py` is a MANAGEMENT tool

---

#### `capture_twitter_cookies.py`
**Purpose:** Capture Twitter cookies using Playwright  
**What it does:**
- Opens Twitter/X login
- Waits for user to log in
- Captures cookies
- Saves to file

**Why it exists:** Automated cookie capture for Twitter  
**Usage:** Run when Twitter cookies expire

**Note:** Similar to `capture_threads_cookies.py` but for Twitter

---

#### `convert_twitter_cookies.py`
**Purpose:** Convert Twitter cookies from one format to another  
**What it does:**
- Converts between cookie formats
- Handles different cookie file structures

**Why it exists:** Format conversion utility  
**Usage:** Run when cookie format changes or migration needed

---

#### `import_twitter_cookies_from_curl.py`
**Purpose:** Import Twitter cookies from curl command  
**What it does:**
- Parses curl command with cookies
- Extracts cookie data
- Converts to JSON format

**Why it exists:** Import cookies from browser dev tools  
**Usage:** Run when manually copying cookies from browser

**Note:** These 5 cookie scripts serve DIFFERENT purposes:
- `manage_cookies.py`: Management/validation
- `capture_*_cookies.py`: Automated capture (2 scripts)
- `convert_twitter_cookies.py`: Format conversion
- `import_*_cookies_from_curl.py`: Manual import

---

### Diagnostic Scripts (moved from other directories)

#### `check_existing_posts.py`
**Purpose:** Check if specific posts exist in database  
**What it does:**
- Queries database for specific post IDs
- Reports existence and metadata

**Why it exists:** Diagnostic tool  
**Usage:** Run to verify post collection

---

#### `check_specific_twitter_posts.py`
**Purpose:** Check specific Twitter posts  
**What it does:**
- Similar to `check_existing_posts.py` but Twitter-specific

**Why it exists:** Twitter-specific diagnostic  
**Usage:** Run to check Twitter post collection

**Note:** Might be redundant with `check_existing_posts.py`

---

#### `check_supabase_posts.py`
**Purpose:** Check posts in Supabase  
**What it does:**
- Queries Supabase for posts
- Reports Supabase-specific metadata

**Why it exists:** Supabase diagnostic  
**Usage:** Run to verify Supabase sync

---

#### `query_by_collected_date.py`
**Purpose:** Query posts by collection date  
**What it does:**
- Filters posts by `collected_at` date
- Reports statistics

**Why it exists:** Date-based query tool  
**Usage:** Run to analyze posts by collection date

---

#### `query_twitter_posts_supabase.py`
**Purpose:** Query Twitter posts from Supabase  
**What it does:**
- Supabase-specific Twitter post queries
- Reports statistics

**Why it exists:** Supabase Twitter diagnostic  
**Usage:** Run to check Twitter posts in Supabase

---

### Management Scripts

#### `manage_profiles.py`
**Purpose:** Manage persona profiles  
**What it does:**
- Create/update/delete profiles
- Configure profile settings

**Why it exists:** Profile management interface  
**Usage:** Run to manage personas

---

#### `update_engagement_metrics.py`
**Purpose:** Update engagement metrics for posts  
**What it does:**
- Fetches engagement data
- Updates database with metrics

**Why it exists:** Keep engagement metrics current  
**Usage:** Run periodically to update metrics

---

#### `update_voice_model.py`
**Purpose:** Update voice model for personas  
**What it does:**
- Updates persona voice patterns
- Regenerates voice embeddings

**Why it exists:** Voice model maintenance  
**Usage:** Run when voice patterns change

---

#### `precompute_persona_embeddings.py`
**Purpose:** Precompute embeddings for personas  
**What it does:**
- Generates embeddings for persona content
- Stores for faster retrieval

**Why it exists:** Performance optimization  
**Usage:** Run when persona content changes

---

#### `generate_ai_summaries.py`
**Purpose:** Generate AI summaries for posts  
**What it does:**
- Uses AI to generate summaries
- Updates database

**Why it exists:** Batch summary generation  
**Usage:** Run to backfill summaries

---

### Other Utilities

#### `analyze_collected_posts.py`
**Purpose:** Analyze collected posts (statistics)  
**What it does:**
- Generates statistics on collected posts
- Reports platform breakdown, date ranges, etc.

**Why it exists:** Analytics tool  
**Usage:** Run to get collection statistics

---

#### `backlog_analysis.py`
**Purpose:** Analyze backlog of unprocessed posts  
**What it does:**
- Identifies unprocessed posts
- Reports backlog size and composition

**Why it exists:** Monitor processing backlog  
**Usage:** Run to check backlog status

---

#### `dashboard.py`
**Purpose:** Generate dashboard/overview  
**What it does:**
- Creates overview of system status
- Reports key metrics

**Why it exists:** System monitoring  
**Usage:** Run for system overview

---

#### `disable_automation.py`
**Purpose:** Disable automation features  
**What it does:**
- Turns off automated posting/collection
- Safety switch

**Why it exists:** Emergency stop  
**Usage:** Run to disable automation

---

#### `fetch_full_content_from_url.py`
**Purpose:** Fetch full content from URL  
**What it does:**
- Scrapes full content from URLs
- Handles truncation

**Why it exists:** Content retrieval utility  
**Usage:** Run to get full content from links

---

## 📝 Key Findings

### Scripts That Serve Different Purposes (NOT Redundant)

1. **Validation Scripts:**
   - `validate_usable_posts.py`: Validates posts that SHOULD be usable (strict)
   - `validate_all_posts.py`: Validates ALL posts (broader)
   - `validate_evergreen_posts.py`: Validates evergreen classification accuracy
   - `comprehensive_validation.py`: Most thorough (includes all edge cases)

2. **Check Scripts:**
   - `check_by_insertion_time.py`: Specific diagnostic (hardcoded post IDs)
   - `check_circuit_breaker_status.py`: API health monitoring
   - `check_sync_status.py`: Database sync health
   - `check_truncation.py`: Content quality check

3. **Cleanup Scripts:**
   - `cleanup_bad_posts.py`: Remove low-quality posts
   - `cleanup_stale_usable_posts.py`: Remove expired time-sensitive posts
   - `cleanup_supabase.py`: Fix corrupted Supabase data
   - `clean_supabase_safe.py`: Safer Supabase cleanup

4. **Cookie Scripts:**
   - `manage_cookies.py`: Management/validation
   - `capture_*_cookies.py`: Automated capture (2 scripts)
   - `convert_twitter_cookies.py`: Format conversion
   - `import_*_cookies_from_curl.py`: Manual import

### Investigation Results: Scripts Are NOT Redundant

After reading the actual code, here are the findings:

#### 1. Cleanup Scripts - DIFFERENT PURPOSES

**`cleanup_supabase.py`:**
- **Purpose:** Full cleanup with multiple options
- **Features:**
  - View latest posts (diagnostic)
  - Delete ALL posts (clean slate)
  - Delete posts from last 24 hours
  - Resync from local database
  - Full cleanup and resync
- **Use case:** Aggressive cleanup when you need to reset or fix major issues
- **Risk level:** HIGH - can delete everything

**`clean_supabase_safe.py`:**
- **Purpose:** Safe cleanup - only removes clearly bad data
- **Features:**
  - Only deletes posts with missing critical fields (post_id, platform, content)
  - Never deletes valid posts
  - Optional sync of missing posts from local
- **Use case:** Safe cleanup when you want to remove bad data without risk
- **Risk level:** LOW - only removes clearly broken posts

**Verdict:** NOT redundant - one is aggressive, one is safe

---

#### 2. Delete Scripts - DIFFERENT PURPOSES

**`delete_posts.py`:**
- **Purpose:** Comprehensive deletion tool with many options
- **Features:**
  - Delete by post IDs
  - Delete by platform
  - Delete by author
  - Delete by content substring
  - Delete by timestamp
  - Dry-run mode
  - Works with both SQLite and Supabase
- **Use case:** General-purpose deletion tool
- **Flexibility:** HIGH - handles many scenarios

**`delete_recent_twitter_posts.py`:**
- **Purpose:** Hardcoded to delete Twitter posts from last 10 minutes
- **Features:**
  - Fixed 10-minute window
  - Twitter-only
  - No options or parameters
- **Use case:** Specific one-time cleanup (probably for a specific incident)
- **Flexibility:** NONE - hardcoded behavior

**`remove_stray_twitter_posts.py`:**
- **Purpose:** Remove specific hardcoded authors and content snippets
- **Features:**
  - Hardcoded list of authors: `DITOGAMES`, `Geomi`, `Sui`, `DigiShares`
  - Hardcoded content snippets
  - Twitter-only
- **Use case:** One-time cleanup of specific stray posts (November 10 incident)
- **Flexibility:** NONE - hardcoded cleanup

**Verdict:** NOT redundant - `delete_posts.py` is general-purpose, the other two are specific one-time scripts

---

#### 3. Check Scripts - DIFFERENT PURPOSES

**`check_existing_posts.py`:**
- **Purpose:** General database overview
- **Features:**
  - Shows total posts
  - Groups by platform
  - Shows last 10 posts
- **Use case:** Quick overview of database contents
- **Scope:** General - all platforms

**`check_specific_twitter_posts.py`:**
- **Purpose:** Twitter-specific diagnostic with keyword/author search
- **Features:**
  - Searches by keywords (zksync, 5090s, EVM block, etc.)
  - Searches by specific authors (drakefjustin, shanaka86, zksync)
  - Shows most recent Twitter posts
  - Checks collection timing (last hour)
  - Provides troubleshooting tips
- **Use case:** Debugging specific Twitter collection issues
- **Scope:** Twitter-specific diagnostic

**Verdict:** NOT redundant - one is general overview, one is Twitter-specific diagnostic

### Scripts Using Deprecated Code

1. **`production_content_pipeline.py`:**
   - Uses `ContentRewriter` (deprecated)
   - Should migrate to `ModularRewriter`

---

## 🎯 Recommendations

### ✅ Keep As-Is (All Serve Different Purposes)
- **All validation scripts:** Different validation scopes (usable, all, evergreen, comprehensive)
- **All check scripts:** Different diagnostic purposes (sync, truncation, circuit breaker, insertion time, general, Twitter-specific)
- **All cleanup scripts:** Different risk levels (aggressive vs safe, bad posts vs stale posts)
- **All delete scripts:** Different use cases (general-purpose vs one-time specific cleanups)
- **Cookie scripts:** Different functions (capture, convert, import, manage)
- **Analysis scripts:** Core functionality (analyze new, fast recategorize, production pipeline)

### 🔄 Migration Needed
1. **`production_content_pipeline.py`:**
   - Currently uses `ContentRewriter` (deprecated)
   - Should migrate to `ModularRewriter`
   - **Priority:** Medium (works but uses deprecated code)

### 📝 Documentation Needed
1. **One-time scripts should be documented:**
   - `delete_recent_twitter_posts.py`: One-time cleanup (10-minute window)
   - `remove_stray_twitter_posts.py`: One-time cleanup (November 10 incident)
   - Consider adding comments: "ONE-TIME SCRIPT - Do not run again"

2. **Create runbooks:**
   - When to use `cleanup_supabase.py` vs `clean_supabase_safe.py`
   - When to use `delete_posts.py` vs specific deletion scripts
   - When to use each validation script

### 🗂️ Organization Suggestions
1. **Consider creating subdirectories:**
   - `database/one_time/` - for one-time cleanup scripts
   - `database/diagnostics/` - for check scripts
   - `database/validation/` - for validation scripts
   - `database/cleanup/` - for cleanup scripts

2. **Add README files:**
   - `database/README.md` - explains when to use each script
   - `utilities/README.md` - explains cookie management workflow

---

## 📈 Next Steps

1. **Compare redundant candidates:**
   - Read full content of potentially redundant scripts
   - Identify actual differences
   - Consolidate if truly redundant

2. **Create unified tools:**
   - Consider creating a unified diagnostic tool that combines check scripts
   - Consider creating a unified deletion tool that handles all cases

3. **Document usage patterns:**
   - Track which scripts are actually used
   - Archive unused scripts
   - Create runbooks for common tasks

