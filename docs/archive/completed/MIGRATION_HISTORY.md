# Database Migration History

**Last Updated:** 2025-11-20  
**Maintained By:** Agent 7 - Database Specialist

---

## Overview

This document tracks all database migrations applied to the BEYONDLINES system. Migrations are versioned and applied in order.

---

## Migration Index

| Date | Migration | Type | Status | Description |
|------|-----------|------|--------|-------------|
| 2025-11-20 | 2025_11_20_database_performance_indexes.sql | Supabase | ✅ Applied | Adds missing performance indexes |
| 2025-11-20 | 2025_11_20_sqlite_indexes.py | SQLite | ✅ Applied | Adds missing SQLite indexes |
| 2025-11-20 | 2025_11_20_remove_unused_columns_safe.sql | Supabase | ✅ Applied | Removes 4 safe unused columns |
| 2025-11-20 | 2025_11_20_remove_unused_columns.sql | Supabase | ⏳ Pending | Removes 8 unused columns (after code updates) |

---

## Migration Details

### 2025-11-20: Database Performance Indexes (Supabase)

**File:** `migrations/2025_11_20_database_performance_indexes.sql`  
**Priority:** P0 - Critical  
**Status:** ✅ Ready to apply

**Purpose:**
Optimize common query patterns by adding missing indexes.

**Indexes Added:**
1. `idx_posts_platform_created_at` - Compound index for platform + created_at queries
2. `idx_posts_platform_value_score` - Compound index for platform + value_score + created_at
3. `idx_posts_rewrite_candidate_score` - Partial index for rewrite candidates

**Expected Impact:**
- 50-90% improvement on filtered/sorted queries
- 80%+ faster platform + time queries
- Most significant improvement on datasets >10k posts

**Apply:**
```bash
# Run in Supabase SQL Editor
# File: migrations/2025_11_20_database_performance_indexes.sql
```

**Verification:**
```sql
-- Check indexes were created
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'posts' 
  AND schemaname = 'public'
ORDER BY indexname;
```

---

### 2025-11-20: SQLite Performance Indexes

**File:** `migrations/2025_11_20_sqlite_indexes.py`  
**Priority:** P0 - Critical  
**Status:** ✅ Ready to apply

**Purpose:**
Add missing indexes to SQLite database for query performance.

**Indexes Added:**
1. `idx_posts_platform_created_at` - Compound index
2. `idx_posts_created_at` - Single column index
3. `idx_posts_value_score` - Single column index
4. `idx_posts_rewrite_score` - Single column index
5. `idx_posts_platform_value_score` - Compound index
6. `idx_posts_rewrite_candidate_score` - Rewrite candidate index

**Apply:**
```bash
python migrations/2025_11_20_sqlite_indexes.py --db-path=beyondlines.db
```

**Verification:**
```bash
python migrations/2025_11_20_sqlite_indexes.py --db-path=beyondlines.db --verify-only
```

---

### 2025-11-20: Remove Safe Unused Columns

**File:** `migrations/2025_11_20_remove_unused_columns_safe.sql`  
**Priority:** P1 - Important  
**Status:** ✅ Applied 2025-11-22

**Purpose:**
Remove 4 confirmed unused columns with zero code references.

**Columns Removed:**
1. `upvote_ratio` - 0% filled, no code references
2. `content_category` - 0% filled, no code references
3. `target_social_media` - 0% filled, no code references
4. `time_sensitivity_reason` - 0% filled, no code references

**Safety:**
✅ All 4 columns verified to have zero code references  
✅ Safe to apply immediately  
✅ No code changes required

**Apply:**
```bash
# Manual step via Supabase Dashboard
# URL: https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc/sql/new
# Copy SQL from: migrations/2025_11_20_remove_unused_columns_safe.sql
```

**Verification:**
```sql
-- Should return 0 rows if successful
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND column_name IN (
    'upvote_ratio', 
    'content_category', 
    'target_social_media', 
    'time_sensitivity_reason'
  );
```

**Expected Impact:**
- Storage savings (~4 columns × row_count)
- Faster queries (smaller row size)
- Cleaner schema

**Documentation:** See `docs/TICKET_7_2_SAFE_COLUMN_REMOVAL.md`

---

### 2025-11-20: Remove Unused Columns (Full)

**File:** `migrations/2025_11_20_remove_unused_columns.sql`  
**Priority:** P1 - Important  
**Status:** ⏳ Pending (requires code updates first)

**Purpose:**
Remove unused columns to optimize schema and reduce storage.

**Columns Removed:**
1. `summary` - Duplicate of `ai_summary` (100% duplicate)
2. `num_comments` - 0% filled (should be in engagement JSON)
3. `upvote_ratio` - 0% filled (should be in engagement JSON)
4. `saved_at` - 0% filled, never used
5. `content_category` - 0% filled, duplicate of `category`
6. `target_social_media` - 0% filled, unused feature
7. `time_sensitivity_reason` - 0% filled, unused feature
8. `is_time_sensitive` - Always false, unused

**Prerequisites:**
1. ✅ Run column analysis: `python scripts/database/analyze_unused_columns.py --supabase`
2. ✅ Check code references: `python scripts/database/check_column_references.py --columns ...`
3. ⏳ Backup database
4. ⏳ Test in staging environment

**Apply:**
```bash
# 1. Backup first
pg_dump -h <host> -U <user> -d <database> -t posts > backup_posts_$(date +%Y%m%d).sql

# 2. Run in Supabase SQL Editor
# File: migrations/2025_11_20_remove_unused_columns.sql
```

**Expected Impact:**
- ~37% storage reduction
- 5-15% query performance improvement
- Better maintainability

**Rollback:**
```sql
-- Restore from backup
psql -h <host> -U <user> -d <database> < backup_posts_YYYYMMDD.sql
```

---

## Previous Migrations

### 2025-11-16: Consolidated Schema

**File:** `migrations/2025_11_16_consolidated_schema.sql`  
**Status:** ✅ Applied

Consolidated all schema changes into a single migration file. Added:
- Core post table structure
- Analysis fields
- Rewrite fields
- Persona fields
- Indexes for performance

### 2025-11-06: Usable Posts Table

**File:** `migrations/2025_11_06_usable_posts_table.sql`  
**Status:** ✅ Applied

Created `usable_posts` table for curated high-quality posts with:
- Essential analysis fields
- Time sensitivity tracking
- Persona matching
- Performance indexes

### 2025-11-04: Analysis, Rewrite, Persona Fields

**File:** `migrations/2025_11_04_analysis_rewrite_persona.sql`  
**Status:** ✅ Applied

Added essential fields for analysis and rewriting:
- `rewrite_score`, `rewrite_readiness`
- `persona_fit_scores`, `best_persona_key`
- Analysis metadata fields

---

## Migration Application Guidelines

### Before Applying

1. **Review Migration:** Read the migration file carefully
2. **Check Dependencies:** Ensure prerequisite migrations are applied
3. **Create Backup:** Always backup before applying migrations
4. **Test in Staging:** Test migrations in staging environment first

### Applying Migrations

**Supabase Migrations:**
1. Open Supabase Dashboard → SQL Editor
2. Click "New Query"
3. Copy migration SQL
4. Click "Run"
5. Verify results

**SQLite Migrations:**
```bash
python migrations/<migration_file>.py --db-path=beyondlines.db
```

### After Applying

1. **Verify:** Run verification queries from migration file
2. **Monitor:** Check application logs for errors
3. **Test:** Test critical queries and operations
4. **Document:** Update this file with application date

---

## Migration Tools

### Apply Migrations

```bash
# List available migrations
python scripts/database/apply_migrations.py --list

# Apply specific migration (dry-run)
python scripts/database/apply_migrations.py --migration migrations/2025_11_20_database_performance_indexes.sql --dry-run

# Apply all migrations
python scripts/database/apply_migrations.py --backup
```

### Monitor Performance

```bash
# Save baseline
python scripts/database/monitor_performance.py --baseline

# Save snapshot
python scripts/database/monitor_performance.py --snapshot

# Compare with baseline
python scripts/database/monitor_performance.py --compare

# Generate report
python scripts/database/monitor_performance.py --report
```

### Verify Migrations

```bash
# Verify specific migration
python scripts/database/apply_migrations.py --verify 2025_11_20_database_performance_indexes.sql

# Check consistency
python scripts/database/check_consistency.py
```

---

## Performance Improvements Tracking

### After Index Migration (Expected)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Platform + Time Queries | Baseline | TBD | 80%+ faster |
| Filtered Queries | Baseline | TBD | 50-90% faster |
| Large Dataset Queries | Baseline | TBD | Significant improvement |

### After Column Removal (Expected)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Storage Size | Baseline | TBD | ~37% reduction |
| Query Performance | Baseline | TBD | 5-15% faster |
| Row Size | Baseline | TBD | Smaller |

*Note: Actual improvements will be measured after migrations are applied.*

---

## Rollback Procedures

### Index Removal

```sql
-- Drop indexes if needed
DROP INDEX IF EXISTS idx_posts_platform_created_at;
DROP INDEX IF EXISTS idx_posts_platform_value_score;
DROP INDEX IF EXISTS idx_posts_rewrite_candidate_score;
```

### Column Restoration

```sql
-- Restore columns from backup
-- See migration file for specific column definitions
ALTER TABLE posts ADD COLUMN summary TEXT;
ALTER TABLE posts ADD COLUMN num_comments INTEGER;
-- ... etc
```

### Full Rollback

```bash
# Restore from backup
pg_dump -h <host> -U <user> -d <database> < backup_posts_YYYYMMDD.sql
```

---

## Notes

1. **Migration Order:** Migrations should be applied in chronological order
2. **Testing:** Always test migrations in staging before production
3. **Backups:** Create backups before any destructive operations
4. **Monitoring:** Monitor performance after migrations
5. **Documentation:** Update this file after applying migrations

---

**Last Updated:** 2025-11-22  
**Last Applied:** 2025-11-22 - Safe column removal migration  
**Next Review:** After full unused columns migration (requires code updates)

