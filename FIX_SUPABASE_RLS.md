# Fix Supabase RLS (Row-Level Security) Issue

## Current Status

✅ **Local Database (SQLite):** Working perfectly - 103+ posts saved
❌ **Supabase:** Empty - All inserts blocked by RLS (401 Unauthorized)

## The Problem

Supabase Row-Level Security (RLS) is blocking ALL insert/update operations because:
1. No RLS policies are configured for the `posts` table
2. Service role key bypasses RLS for reads, but not for client-side operations
3. PostInserter is using the client API which enforces RLS

## Solution Options

### Option 1: Disable RLS (Quick Fix - NOT RECOMMENDED for production)

In Supabase dashboard:
1. Go to **Authentication > Policies**
2. Find `posts` table
3. Click **"Disable RLS"** button

**Pros:** Immediate fix, works instantly
**Cons:** Security risk - anyone with your Supabase URL can write to the table

### Option 2: Add Permissive RLS Policy (RECOMMENDED for development)

Run this SQL in Supabase SQL Editor:

```sql
-- Allow all operations from service role
CREATE POLICY "Allow service role full access"
ON public.posts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Or allow all operations (less secure)
CREATE POLICY "Allow all operations"
ON public.posts
FOR ALL
USING (true)
WITH CHECK (true);
```

**Pros:** Keeps RLS enabled, allows inserts
**Cons:** Still allows anyone to insert (need auth for production)

### Option 3: Add Authenticated User Policy (RECOMMENDED for production)

```sql
-- Allow authenticated users to insert their own posts
CREATE POLICY "Users can insert posts"
ON public.posts
FOR INSERT
TO authenticated
WITH CHECK (true);

-- Allow authenticated users to read all posts
CREATE POLICY "Users can read posts"
ON public.posts
FOR SELECT
TO authenticated, anon
USING (true);
```

**Pros:** Secure, proper authentication
**Cons:** Requires Supabase authentication setup

### Option 4: Use Service Role Key Directly (CURRENT WORKAROUND)

The code ALREADY uses service role key, but PostInserter uses client API which still enforces RLS. 

We can bypass RLS by using direct SQL inserts instead of client API:

```python
# Instead of: client.table().insert()
# Use: client.rpc() with SQL
```

### Option 5: Just Use Local SQLite (CURRENT STATE)

**This is what's happening now:**
- All posts saved to `prismind.db` locally ✅
- Supabase is just a "nice to have" backup/sync
- Collection works perfectly without Supabase

**Recommendation:** Keep using local SQLite as primary, fix Supabase later when needed.

## Quick Fix Command

Run this in Supabase SQL Editor to allow all inserts:

```sql
-- Drop existing restrictive policies (if any)
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.posts;
DROP POLICY IF EXISTS "Enable read access for all users" ON public.posts;

-- Add permissive policy
CREATE POLICY "Allow all operations" 
ON public.posts 
FOR ALL 
USING (true) 
WITH CHECK (true);
```

## Verify Fix

After applying policy, test with:

```bash
python -c "
from src.supabase_manager import SupabaseManager

sm = SupabaseManager()

# Try inserting a test post
test_post = {
    'post_id': 'test_12345',
    'platform': 'test',
    'title': 'Test Post',
    'content': 'Testing RLS fix',
    'url': 'https://test.com',
    'author': 'Test User',
    'created_at': '2025-01-12T00:00:00'
}

result = sm.insert_post(test_post)
print(f'Insert result: {result}')

# Check if it's there
check = sm.client.table('posts').select('*').eq('post_id', 'test_12345').execute()
print(f'Found: {len(check.data)} rows')
"
```

## Current Workaround

**No action needed** - collection is working with local SQLite. Supabase sync can be fixed later when you need cloud backup/access.
