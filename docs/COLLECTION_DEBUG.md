# Collection Debugging Guide

## Issue: Newly Collected Posts Not Appearing in Supabase

### Current Status
- ✅ Supabase connection: Working
- ✅ Post validation: Working
- ✅ Post saving: Working (test posts save successfully)
- ❌ **Collection**: Finding tweets but extracting 0 bookmarks

### Root Cause
The Twitter collector is:
1. ✅ Successfully authenticating
2. ✅ Navigating to bookmarks page
3. ✅ Finding 11 tweets on the page
4. ❌ **Extracting 0 bookmarks** (extraction logic failing)

### Debugging Steps

1. **Check Collection Logs**
   ```bash
   python3 scripts/test_twitter_collector.py
   ```
   Look for: "✅ Found X tweets" vs "✅ Extracted X bookmarks"

2. **Check if Posts Were Actually Saved**
   ```python
   # Check Supabase for recent posts
   from src.database.manager import SupabaseManager
   sm = SupabaseManager()
   result = sm.client.table('posts').select('*').order('collected_at', desc=True).limit(10).execute()
   ```

3. **Check Validation Failures**
   - Look for logs: "❌ Supabase: Post validation failed"
   - Check if posts are being rejected by validator

4. **Check Duplicate Detection**
   - Posts might be marked as duplicates
   - Check duplicate detector cache

### Likely Issues

1. **Tweet Extraction Failing**
   - `_extract_tweet()` returning `None` for all tweets
   - Tweet ID extraction failing (line 174-185 in bookmarks.py)
   - Author extraction failing

2. **All Posts Marked as Duplicates**
   - Existing IDs cache too large
   - URL normalization causing false duplicates

3. **Validation Rejecting All Posts**
   - Posts missing required fields
   - Content too short
   - Author is placeholder

### Next Steps

1. Add more logging to `_extract_tweet()` to see why extraction fails
2. Check if tweet ID extraction is working
3. Verify posts aren't being filtered as duplicates
4. Check validation errors in logs
