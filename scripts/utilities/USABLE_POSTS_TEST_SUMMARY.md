# Usable Posts - Test Summary

## Test Results

### ✅ All Tests Passing

**Test 1: Content Quality Checks**
- ✅ Valid content: PASSED
- ✅ Truncated content: PASSED (correctly rejects)
- ✅ Too short content: PASSED (correctly rejects)
- ✅ JSON-wrapped summary: PASSED (correctly extracts)
- ✅ Placeholder content: PASSED (correctly rejects)

**Test 2: Time-Sensitive Keyword Detection**
- ✅ Breaking news: PASSED
- ✅ Just released: PASSED
- ✅ Evergreen content: PASSED
- ✅ Time reference: PASSED
- ✅ Crypto analysis (evergreen): PASSED

**Test 3: Complete Curation Logic**
- ✅ Found 173 usable posts
- ✅ Validation matches curation script results
- ✅ All exclusion logic working correctly

**Test 4: Data Integrity**
- ✅ All 173 usable posts have valid data
- ✅ All required fields present
- ✅ All scores valid (> 0)
- ✅ All content quality checks passed

## Final Statistics

### Usable Posts: 173 (42.8% of analyzed posts)
- **Truly evergreen**: 147 posts (7 days - 6 months old, verified as timeless)
- **Fresh time-sensitive**: 26 posts (≤7 days old)

### Exclusions
- **Content quality issues**: 30 posts (7.4%)
  - Truncated content
  - Placeholder/error content
  - Invalid summaries

- **Time-sensitive keywords**: 71 posts (17.6%)
  - Caught false positives (time-sensitive content marked as evergreen)
  - Breaking news language
  - Recent event references

- **Other reasons**: 130 posts (32.2%)
  - Age requirements (too old or too recent)
  - Category issues (DEPRECATED, NEWS)
  - Missing required fields

## Validation Results

✅ **Validation confirms curation script results:**
- Curation script: 173 usable posts
- Validation script: 173 usable posts
- **Perfect match!**

## Content Quality Checks

✅ **All checks working correctly:**
- Truncation detection (ends with `...`, mid-sentence)
- Placeholder/error content detection
- AI summary validation and JSON extraction
- Title quality checks (relaxed)
- Minimum content length validation

## Time-Sensitive Keyword Detection

✅ **Keyword detection working correctly:**
- High-confidence patterns (breaking, just released, today, etc.)
- Medium-confidence patterns (this week, recently, etc.)
- Word boundary matching (prevents false positives)
- Crypto/topic keywords excluded (allows evergreen crypto content)

## Next Steps

1. ✅ **Migration script ready**: `migrations/2025_11_06_usable_posts_table.sql`
2. ✅ **Curation script tested**: `scripts/curate_usable_posts.py`
3. ✅ **Validation script tested**: `scripts/validate_usable_posts.py`
4. ✅ **Workflow tests passing**: `scripts/test_usable_posts_workflow.py`
5. ⏳ **Apply migration to Supabase**: Run migration SQL in Supabase SQL Editor
6. ⏳ **Populate table**: Run `python scripts/curate_usable_posts.py`
7. ⏳ **Set up auto-refresh**: Daily cleanup job or trigger on new analysis

## Ready for Production

✅ All tests passing
✅ Data quality validated
✅ Content analysis working
✅ Curation logic verified
✅ Ready to populate `usable_posts` table




