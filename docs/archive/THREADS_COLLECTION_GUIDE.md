# Threads Collection & Analysis Guide

## What We Fixed

The Threads extractor was collecting **username spam** instead of actual content:
- ❌ Before: "makhambet_askhat makhambet_askhat makhambet_askhat..."
- ✅ After: "если вы устали искать работу/удаленку заграницей только на LinkedIn..."

**Root cause**: DOM selectors were overwriting properly extracted meta tag content.

**Solution**: 
1. Extract content from meta tags first (most reliable)
2. Extract author/handle from `og:title` meta tag  
3. Only fallback to DOM selectors if meta tags fail

---

## Collection Scripts

### 1. Quick Collection (10-15 posts)
```bash
python3 collect_threads_now.py
```
- Collects ~10 new posts
- Includes AI analysis
- Syncs to Supabase

### 2. Bulk Collection (customize limit)
```bash
# Collect 50 posts with analysis
python3 collect_threads_bulk.py --limit 50

# Collect 30 posts WITHOUT analysis (faster)
python3 collect_threads_bulk.py --limit 30 --no-analysis
```

### 3. Direct Extractor Test
```python
from src.core.extraction.threads_extractor import ThreadsExtractor

extractor = ThreadsExtractor()
posts = await extractor.scrape_posts_from_urls_async([
    'https://www.threads.net/@unwind_ai/post/DNHgfaQIWXF'
])
```

---

## AI Analysis Workflow

### What the Analyzer Does

The `IntelligentContentAnalyzer` provides:

1. **Category Classification**: Tech, Business, Education, etc.
2. **Topic Extraction**: Main subject of the post
3. **Value Scoring**: 1-10 score based on usefulness
4. **Sentiment Analysis**: Positive, Negative, Neutral
5. **Key Concepts**: Important terms and ideas
6. **Summary**: AI-generated summary
7. **Tags**: Relevant hashtags and keywords

### Manual Analysis Example

```python
import asyncio
from src.services.new_database_manager import NewDatabaseManager
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer

async def analyze_posts():
    db = NewDatabaseManager()
    analyzer = IntelligentContentAnalyzer()
    
    # Get unanalyzed posts
    posts = db.get_unanalyzed_posts(limit=5, platforms=['threads'])
    
    for post in posts:
        # Analyze
        analysis = await analyzer.analyze_content(post)
        
        # Save results
        db.update_post(post['post_id'], {
            'category': analysis.get('category'),
            'topic': analysis.get('topic'),
            'value_score': analysis.get('value_score'),
            'sentiment': analysis.get('sentiment'),
            'summary': analysis.get('summary'),
            'analyzed_at': analysis.get('analyzed_at')
        })

asyncio.run(analyze_posts())
```

### Automatic Analysis

Analysis runs automatically when:
- Using `collect_threads_bulk.py` (default)
- `NewDatabaseManager.add_post()` is called
- Supabase adapter has `AUTO_ANALYZE_POSTS=true`

To disable auto-analysis:
```bash
export SKIP_AI_ANALYSIS=true
# or in config/collection.json:
{"performance": {"skip_ai_analysis": true}}
```

---

## Database Queries

### Get Statistics
```python
db = NewDatabaseManager()

# Total posts by platform
threads_posts = db.get_posts_by_platform('threads')
print(f"Total Threads: {len(threads_posts)}")

# Unanalyzed posts
unanalyzed = db.get_unanalyzed_posts(limit=100, platforms=['threads'])
print(f"Need analysis: {len(unanalyzed)}")

# High quality posts
high_quality = db.get_high_quality_posts(min_quality=7.0, limit=50)
print(f"High quality: {len(high_quality)}")

# Database stats
stats = db.get_database_stats()
print(stats)
```

### Query by Category
```python
# Get posts by score range
top_posts = db.get_posts_by_score_range(min_score=8.0, max_score=10.0)

# Get rewrite candidates
candidates = db.get_rewrite_candidates(limit=50)
```

---

## Supabase Sync

### Check Sync Status
```python
from supabase import create_client
import os

client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Get Threads posts count
result = client.table('posts').select('id').eq('platform', 'threads').execute()
print(f"Supabase Threads posts: {len(result.data)}")

# Get latest posts
latest = client.table('posts')\
    .select('*')\
    .eq('platform', 'threads')\
    .order('created_at', desc=True)\
    .limit(5)\
    .execute()

for post in latest.data:
    print(f"{post['author']}: {post['content'][:60]}...")
```

### Clean Bad Posts
```python
# Delete posts with bad author data
client.table('posts')\
    .delete()\
    .eq('platform', 'threads')\
    .eq('author_handle', 'unknown')\
    .execute()
```

---

## Current Status

### Database
- **Total Threads posts**: 14
- **Properly extracted**: ✅ All (after fix)
- **With AI analysis**: 0 (pending)
- **Synced to Supabase**: 4

### What Works
✅ Content extraction from meta tags  
✅ Author name and handle extraction  
✅ Language detection (Russian/English)  
✅ Supabase sync  
✅ Duplicate detection  
✅ Cookie-based authentication  

### What's Next
1. Run bulk analysis on existing posts
2. Collect more posts (currently at 14, can get 40+)
3. Set up scheduled collection
4. Enable embedding generation for semantic search

---

## Tips & Tricks

### Speed Up Collection
- Use `--no-analysis` flag for faster collection
- Set `SKIP_AI_ANALYSIS=true` in environment
- Increase scroll count in script for more posts per run

### Best Practices
1. Run analysis separately from collection for large batches
2. Check cookie expiration regularly
3. Monitor Supabase quota
4. Use language detection to filter relevant content

### Troubleshooting

**Cookie expired?**
```bash
python3 scripts/capture_threads_cookies.py
```

**Analysis too slow?**
- Use local Ollama instead of API calls
- Reduce batch size
- Skip media analysis

**Posts not syncing to Supabase?**
- Check duplicate detection
- Verify Supabase credentials
- Check RLS policies

---

## Example Workflow

```bash
# 1. Collect posts with analysis
python3 collect_threads_bulk.py --limit 30

# 2. Check what was collected
python3 -c "
from src.services.new_database_manager import NewDatabaseManager
db = NewDatabaseManager()
posts = db.get_posts_by_platform('threads')
for p in posts[:5]:
    print(f\"{p['author']}: {p['content'][:80]}...\")
"

# 3. Analyze unanalyzed posts
python3 demo_analyzer.py

# 4. Query analyzed posts
python3 -c "
from src.services.new_database_manager import NewDatabaseManager
db = NewDatabaseManager()
high_value = db.get_posts_by_score_range(7.0, 10.0)
print(f'Found {len(high_value)} high-value posts')
"
```
