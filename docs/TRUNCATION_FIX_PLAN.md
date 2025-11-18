# Truncation Fix Plan

## Problem
- **8/20 posts (40%) are truncated** - content cut off mid-sentence
- Truncated posts end with: commas, "and", "but for", "was", "text and", etc.
- Re-collection script can't find them because Twitter only shows 11 tweets

## Solution Strategy

### Phase 1: Detection ✅ DONE
- ✅ Added `detect_content_truncation()` to analyzer
- ✅ Detects: ellipsis, "show more", mid-sentence cuts, connecting words
- ✅ Marks posts as `is_potentially_truncated`

### Phase 2: Marking Posts
- ✅ Created `scripts/mark_truncated_posts.py` to identify truncated posts
- Run this to see how many need fixing

### Phase 3: Re-collection Options

#### Option A: Wait and Re-collect (Recommended)
1. Mark truncated posts
2. Wait for them to appear in bookmarks (they might be further down)
3. Run re-collection script periodically
4. **Pros**: Simple, works with existing system
5. **Cons**: Slow, depends on Twitter loading more

#### Option B: Direct URL Fetch
1. Use the post URL to fetch full content directly
2. Parse the tweet page HTML
3. Extract full content
4. **Pros**: Fast, doesn't depend on bookmarks
5. **Cons**: More complex, might get rate-limited

#### Option C: Improve Scrolling
1. Make collector scroll more aggressively
2. Wait longer between scrolls
3. Try different scroll patterns
4. **Pros**: Fixes root cause
5. **Cons**: Might still not load enough

### Phase 4: Prevention ✅ DONE
- ✅ "Read more" button clicking is working
- ✅ New posts will get full content automatically
- ✅ Detection will catch any that slip through

## Immediate Actions

1. **Run detection**:
   ```bash
   python3 scripts/mark_truncated_posts.py --limit 100
   ```

2. **Try re-collection** (if posts are in bookmarks):
   ```bash
   python3 scripts/recollect_truncated_tweets.py --limit 50
   ```

3. **For future**: New posts will automatically get full content

## Long-term Solution

The best approach is **Option A + Option B**:
- Use re-collection script for posts that appear in bookmarks
- Use direct URL fetch for posts that don't appear
- Both run periodically to catch all truncated posts
