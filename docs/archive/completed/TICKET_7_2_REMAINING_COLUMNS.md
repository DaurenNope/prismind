# Remaining Column Removal - Code Updates Required

**Date:** 2025-11-22  
**Status:** ⚠️ **Code Updates Required After Migration**

---

## ⚠️ Important Note

After applying `migrations/APPLY_REMAINING_COLUMN_REMOVAL.sql`, you'll need to update the codebase to remove references to the dropped columns.

---

## Columns Being Removed

### 1. `summary` ✅ Mostly Safe
- **Status:** Duplicate of `ai_summary`
- **References:** 440 found, but most are false positives (word "summary" in print statements)
- **Action:** Verify no actual column usage, remove if safe

### 2. `num_comments` ✅ Safe
- **Status:** Column is 0% filled
- **References:** Uses `engagement.get("num_comments")` which is JSONB, not the column
- **Action:** No code changes needed (column not used)

### 3. `saved_at` ⚠️ Code Update Required
- **Status:** Column used in queries
- **Files to Update:**
  - `src/database/queries.py` lines 59, 64
  - `src/core/extraction/reddit_extractor.py` lines 747, 787
  - `src/core/extraction/social_extractor_base.py` lines 26, 49

**Current Code:**
```python
# src/database/queries.py
ORDER BY COALESCE(saved_at, created_at, updated_timestamp, created_timestamp) DESC
```

**Update To:**
```python
ORDER BY COALESCE(created_at, updated_timestamp, created_timestamp) DESC
```

### 4. `is_time_sensitive` ⚠️ Code Update Required
- **Status:** Calculated field stored in DB
- **Files to Update:**
  - `src/core/analysis/analysis_components.py` line 545
  - `src/core/analysis/intelligent_content_analyzer.py` line 169

**Current Code:**
```python
is_time_sensitive = urgency >= 0.35
# ... stores in database
```

**Update To:**
```python
# Just calculate when needed, don't store
# Can use: urgency_score >= 0.35 directly
```

---

## Quick Fix Guide

### Fix `saved_at` References

**File: `src/database/queries.py`**
```python
# Line 59 - Change:
query = (
    "SELECT * FROM posts "
    "ORDER BY COALESCE(saved_at, created_at, updated_timestamp, created_timestamp) DESC"
)

# To:
query = (
    "SELECT * FROM posts "
    "ORDER BY COALESCE(created_at, updated_timestamp, created_timestamp) DESC"
)

# Line 64 - Same change:
query = (
    "SELECT * FROM posts WHERE deleted = 0 "
    "ORDER BY COALESCE(saved_at, created_at, updated_timestamp, created_timestamp) DESC"
)

# To:
query = (
    "SELECT * FROM posts WHERE deleted = 0 "
    "ORDER BY COALESCE(created_at, updated_timestamp, created_timestamp) DESC"
)
```

**File: `src/core/extraction/reddit_extractor.py`**
- Remove `saved_at=` parameters from post dictionaries (lines 747, 787)

**File: `src/core/extraction/social_extractor_base.py`**
- Remove `saved_at` field from class definition (line 26)
- Remove validation code (line 49)

### Fix `is_time_sensitive` References

**File: `src/core/analysis/analysis_components.py`**
- Line 545: Remove storing `is_time_sensitive` in result
- Use `urgency_score >= 0.35` directly when needed

**File: `src/core/analysis/intelligent_content_analyzer.py`**
- Line 169: Remove storing `is_time_sensitive` in result
- Use `urgency_score >= 0.35` directly when needed

---

## Verification After Code Updates

```bash
# Check for any remaining references
grep -r "saved_at" src/
grep -r "is_time_sensitive" src/

# Should return minimal results (only in comments or unrelated contexts)
```

---

## Summary

**Safe to Remove:**
- ✅ `summary` (duplicate of ai_summary)
- ✅ `num_comments` (not used in code)

**Requires Code Updates:**
- ⚠️ `saved_at` - Remove from queries and extractors
- ⚠️ `is_time_sensitive` - Remove storage, calculate on-demand

**Impact:** Minimal - all columns are either unused or can be calculated dynamically.






