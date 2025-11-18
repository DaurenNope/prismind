# 🚀 How to Run BEYONDLINES

## Quick Start

### 1. Start the FastAPI Backend (REQUIRED)
```bash
# In terminal 1
cd /Users/mac/Documents/Development/beyondlines
python3 src/api/main.py
# Or use uvicorn directly:
# uvicorn src.api.main:app --reload --port 8000
```

The API will run on: **http://localhost:8000**
API docs: **http://localhost:8000/docs**

### 2. Start the Svelte UI (Frontend)
```bash
# In terminal 2
cd /Users/mac/Documents/Development/beyondlines/frontend
npm install  # First time only
npm run dev
```

Then open: **http://localhost:5173** (or port shown in terminal)

---

## Kill Running Processes

If you need to stop everything:
```bash
# Kill all backend/frontend processes
lsof -ti:8501 | xargs kill -9 2>/dev/null  # Svelte (if running)
lsof -ti:8000 | xargs kill -9 2>/dev/null  # FastAPI
lsof -ti:5173 | xargs kill -9 2>/dev/null  # Svelte/Vite

# Or kill by process name
pkill -f "svelte"
pkill -f "uvicorn"
pkill -f "fastapi"
```

## Quick Start Scripts

**Start Backend:**
```bash
./scripts/start_backend.sh
```

**Start Frontend:**
```bash
./scripts/start_frontend.sh
```

### 3. Run Collection

**Option A: From Svelte UI**
- Open the Svelte UI (step 1)
- Go to "Collection" tab
- Click "Collect" button for desired platform

**Option B: Command Line**
```bash
# Twitter collection
python3 scripts/test_twitter_collector.py

# All platforms
python3 scripts/run_full_collection.py

# Via main script
python3 main.py collect
```

---

## Collection Scripts

### Twitter Bookmarks
```bash
python3 scripts/test_twitter_collector.py
```

### Reddit Bookmarks
```bash
python3 -c "
from src.pipeline.orchestrator import Orchestrator
import asyncio

async def collect():
    orch = Orchestrator()
    count = await orch.collect_platform('reddit')
    print(f'Collected: {count} posts')

asyncio.run(collect())
"
```

### Threads Bookmarks
```bash
python3 scripts/collect_threads_only.py
```

---

## Check Results

### View Recent Posts in Supabase
```bash
python3 -c "
from src.database.manager import SupabaseManager
sm = SupabaseManager()
result = sm.client.table('posts').select('post_id, platform, collected_at').order('collected_at', desc=True).limit(10).execute()
for post in result.data:
    print(f\"{post.get('post_id')} - {post.get('collected_at')}\")
"
```

### Check Collection Logs
```bash
python3 -c "
from src.database.manager import SupabaseManager
sm = SupabaseManager()
result = sm.client.table('collection_logs').select('*').order('started_at', desc=True).limit(5).execute()
for log in result.data:
    print(f\"{log.get('platform')}: {log.get('posts_collected')} posts at {log.get('started_at')}\")
"
```

---

## System Status

✅ **Database Unification**: Complete
✅ **ID Generation**: Deterministic
✅ **collected_at**: Always set
✅ **Post Saving**: Working
✅ **Command Line**: Primary interface

---

## Troubleshooting

### Collection Returns 0 Posts
- Check Twitter cookies are valid
- Check if posts are duplicates (already in Supabase)
- Check extraction logs for errors

### Posts Not in Supabase
- Check validation errors in logs
- Verify Supabase connection
- Check duplicate detection
