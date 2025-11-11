# Usable Posts Analysis - Validation Results

## Current Status

### Total Usable Posts: 238
- **Truly evergreen**: 211 posts (7 days - 6 months old)
- **Fresh time-sensitive**: 27 posts (≤7 days old)

### Validation Results

✅ **Good:**
- All evergreen posts are at least 7 days old (verified as timeless)
- All fresh time-sensitive posts are ≤7 days old
- No DEPRECATED posts included
- No posts with high urgency (≥0.35) marked as evergreen
- No posts with time_sensitive=True marked as evergreen
- No NEWS category posts marked as evergreen

❌ **Issues Found:**
- 8 posts that are exactly 6.0 months old (should be excluded)
- Some "evergreen" posts might be recent content with low urgency, not truly timeless
- Sample posts show mix of:
  - Educational content (truly evergreen) ✅
  - Recent tech announcements (time-sensitive) ❌
  - Breaking news (time-sensitive) ❌
  - Recent discussions (might be time-sensitive) ❌

## Concerns

### 1. Are "Evergreen" Posts Truly Reusable?

**Sample Analysis:**
- Posts about recent product launches (e.g., "Grok 4 and Perplexity Comet released this week") are NOT evergreen - they're time-sensitive
- Posts about breaking news (e.g., "BREAKING: The $1.5 Trillion Checkmate") are NOT evergreen - they're news
- Posts about educational content (e.g., "Learn how to create YouTube videos") ARE evergreen ✅

**The Problem:**
The classification is based on `urgency_score` and `time_sensitive` flags, but these might not always accurately capture whether content is truly "evergreen" (timeless) or just "recent content with low urgency".

### 2. Age Distribution

- **7-30 days**: 35 posts (might be recent content, not truly evergreen)
- **1-3 months**: 52 posts (more likely to be evergreen)
- **3-6 months**: 124 posts (most likely to be evergreen)
- **>6 months**: 8 posts (should be excluded)

## Recommendations

### Option 1: Stricter Age Requirements (RECOMMENDED)
- Require evergreen posts to be at least **2-4 weeks old** (instead of 7 days)
- This ensures posts are verified as truly timeless before being marked as "evergreen"
- Would reduce false positives (recent content misclassified as evergreen)

### Option 2: Content-Type Filtering
- Only include posts that are clearly evergreen (e.g., educational, how-to, tutorials)
- Exclude posts about recent events, product launches, or news
- This would require analyzing the actual content, not just metadata

### Option 3: Conservative Approach
- Only include posts that are **1-3 months old** as "evergreen"
- This ensures posts are recent enough to be relevant but old enough to be verified as timeless
- Would reduce the number of usable posts but increase quality

### Option 4: Hybrid Approach
- Keep current logic but add a "quality check" that excludes posts with certain keywords (e.g., "BREAKING", "released this week", "just announced")
- This would catch time-sensitive content that was misclassified as evergreen

## Next Steps

1. **Fix the 6-month exclusion** (currently >= 6.0 months, should be >= 6.0 months)
2. **Consider stricter age requirements** (e.g., require evergreen posts to be at least 2-4 weeks old)
3. **Add content analysis** to verify posts are truly evergreen (not just recent content with low urgency)
4. **Test with stricter criteria** to see how many posts are truly reusable

## Current Criteria (Strict)

✅ **Evergreen Posts:**
- `relevance_window = 'evergreen'`
- `urgency_score < 0.35`
- `time_sensitive = False`
- `category != 'NEWS'`
- `category != 'DEPRECATED'`
- Age: **7 days - 6 months** (should be **2-4 weeks - 6 months** for stricter quality)

✅ **Fresh Time-Sensitive Posts:**
- `relevance_window IN ('same-day', '24-72h', 'this-week')`
- Age: **≤7 days**
- `category != 'DEPRECATED'`

## Questions to Answer

1. **Are posts that are 7-30 days old truly "evergreen"?**
   - They might just be recent content with low urgency
   - Should we require at least 2-4 weeks old?

2. **Are posts about recent tech announcements "evergreen"?**
   - They're time-sensitive (product launches, updates)
   - Should we exclude them even if they have low urgency?

3. **Are posts about breaking news "evergreen"?**
   - They're clearly time-sensitive
   - Should we add keyword filtering to catch them?

4. **What makes content truly "evergreen"?**
   - Educational content (tutorials, how-to guides) ✅
   - Timeless advice (life lessons, productivity tips) ✅
   - Recent events (product launches, news) ❌
   - Time-sensitive discussions ❌

## Conclusion

The current logic is **mostly correct** but might be **too permissive**. We should:
1. Fix the 6-month exclusion bug
2. Consider stricter age requirements (2-4 weeks minimum)
3. Add content analysis to verify posts are truly evergreen
4. Test with stricter criteria to ensure only truly reusable content is included



