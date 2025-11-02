# How to Analyze Everything Properly

## Current Situation

- **Supabase**: 589 posts, 211 WITHOUT ai_summary (36%)
- **Speed**: CLI analyzer is SLOW (30 seconds per post = 2+ hours!)
- **Issues**: Duplicate detection, Supabase sync failures, schema mismatches

## Best Way to Analyze All Posts

### Option 1: Use the UI (Recommended) ✅

**Why**: Live progress, batch control, faster

```
1. Go to http://localhost:8501
2. Click "🤖 Analysis" tab
3. Set batch size to 50
4. Click "Run AI Analysis"
5. Watch live progress
6. Repeat until all 211 are analyzed
```

**Time**: ~10-15 minutes per 50 posts = ~40 minutes total

### Option 2: CLI with Batches

```bash
# Analyze in batches of 50
for i in {1..5}; do
  python3 -c "
from src.services.analysis_service import analyze_recent_posts
result = analyze_recent_posts(limit=50, unanalyzed_only=True)
print(f'Batch $i: {result.get(\"processed\", 0)} analyzed')
"
  sleep 5
done
```

### Option 3: Skip Analysis for RSS

RSS posts don't need AI analysis - they have categories already!

```python
# Just mark RSS as analyzed with basic data
from src.services.new_database_manager import NewDatabaseManager
from src.supabase_manager import SupabaseManager

db = NewDatabaseManager()
sb = SupabaseManager()

# Get unanalyzed RSS posts
posts = db.get_posts(limit=1000, platforms=['rss'])

for post in posts:
    if not post.get('ai_summary'):
        # Use RSS title/description as summary
        update = {
            'ai_summary': post.get('title') or post.get('content')[:200],
            'category': post.get('category') or 'News',
            'sentiment': 'neutral',
            'value_score': 5.0,
        }
        
        # Update in Supabase
        sb.client.table('posts').update(update).eq('post_id', post['post_id']).execute()
```

## Why Analyzer is Slow

1. **Ollama timeouts**: Qwen model is slow
2. **API calls**: Mistral (401), Gemini (invalid key) all failing
3. **Duplicate checks**: Checking Supabase for every post
4. **Schema mismatches**: Missing `analysis_version` column
5. **Vision analysis**: Trying to analyze invalid URLs

## Quick Wins

### 1. Disable Failed APIs

Edit `.env`:
```bash
# Comment out broken APIs
# MISTRAL_API_KEY=...
# GEMINI_API_KEY=...
```

Only use Ollama (local, no API limits)

### 2. Skip RSS Analysis

Mark all RSS as "analyzed" with basic data (they don't need AI)

### 3. Use Faster Model

```bash
# Instead of qwen2.5:7b, use smaller model
# Edit config to use qwen2.5:1.5b (4x faster)
```

## Recommendation

**Best approach**:
1. Mark 6 RSS posts as analyzed (manual)
2. Use UI to analyze remaining 205 posts in batches of 50
3. Total time: ~45 minutes

**Alternative** (if you want it done NOW):
- Just use what you have (64% analyzed is pretty good!)
- Analyze more later as needed
- Focus on collecting more content first

## Bottom Line

You have 3 choices:
1. ✅ **Use UI** - 40-50 mins, live progress, controlled
2. ⚠️ **CLI batches** - ~2 hours, no control, errors
3. 🎯 **Skip for now** - 64% is usable, analyze more later

**I recommend: Use the UI, analyze in batches of 50!**
