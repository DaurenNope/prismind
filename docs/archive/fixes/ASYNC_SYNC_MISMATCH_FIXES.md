# Async/Sync Mismatch Fixes

**Date**: 2025-01-11  
**Status**: ✅ Infrastructure Complete, Patterns Documented

## Overview

This document addresses async/sync mismatches across the codebase by providing utilities and patterns for properly handling async operations.

## Problem

Common async/sync mismatches:
1. **Sync HTTP requests** (`requests.get/post`) called in async functions
2. **Sync database operations** (`sqlite3.connect`, `cursor.execute`) in async functions
3. **Blocking I/O** (`time.sleep`, file I/O) in async functions
4. **Missing await** on async operations
5. **Sync operations** blocking the event loop

## Solution: Async I/O Utilities

Created `src/utils/async_io.py` with utilities for:

### 1. Executor Wrapper

Run sync operations in thread pool without blocking event loop:

```python
from src.utils.async_io import run_in_executor

async def my_async_function():
    # Run sync operation in executor
    result = await run_in_executor(some_sync_function, arg1, arg2)
```

### 2. Async HTTP Client

Async HTTP requests with proper timeout handling:

```python
from src.utils.async_io import async_http_get, async_http_post

async def fetch_data():
    response = await async_http_get(
        "https://api.example.com/data",
        params={"key": "value"},
        timeout=30.0
    )
    return response['data']
```

**Implementation**:
- Uses `aiohttp` if available (native async)
- Falls back to `requests` in executor if `aiohttp` not installed

### 3. Async SQLite Wrapper

Async database operations:

```python
from src.utils.async_io import async_sqlite_connect

async def query_data():
    async with async_sqlite_connect("db.sqlite") as conn:
        cursor = await conn.execute("SELECT * FROM posts")
        rows = await cursor.fetchall()
        return rows
```

**Implementation**:
- Uses `aiosqlite` if available (native async)
- Falls back to `sqlite3` in executor if `aiosqlite` not installed

### 4. Sync-to-Async Decorator

Convert sync functions to async automatically:

```python
from src.utils.async_io import sync_to_async

@sync_to_async
def my_sync_function(x, y):
    return x + y

# Now can be called with await
result = await my_sync_function(1, 2)
```

## Fixed Patterns

### Pattern 1: HTTP Requests in Async Functions

**Before** (Blocking):
```python
async def fetch_user_data():
    response = requests.get("https://api.example.com/user")  # Blocks!
    return response.json()
```

**After** (Non-blocking):
```python
from src.utils.async_io import async_http_get

async def fetch_user_data():
    response = await async_http_get("https://api.example.com/user")
    return response['data']
```

### Pattern 2: Database Operations in Async Functions

**Before** (Blocking):
```python
async def get_posts():
    conn = sqlite3.connect("db.sqlite")  # Blocks!
    cursor = conn.execute("SELECT * FROM posts")
    return cursor.fetchall()
```

**After** (Non-blocking):
```python
from src.utils.async_io import async_sqlite_connect, run_in_executor

async def get_posts():
    async with async_sqlite_connect("db.sqlite") as conn:
        cursor = await conn.execute("SELECT * FROM posts")
        rows = await cursor.fetchall()
        return rows
```

Or using executor:
```python
from src.utils.async_io import run_in_executor

async def get_posts():
    def _sync_get():
        conn = sqlite3.connect("db.sqlite")
        cursor = conn.execute("SELECT * FROM posts")
        return cursor.fetchall()
    
    return await run_in_executor(_sync_get)
```

### Pattern 3: Sleep in Async Functions

**Before** (Blocking):
```python
import time

async def wait():
    time.sleep(5)  # Blocks event loop!
```

**After** (Non-blocking):
```python
import asyncio

async def wait():
    await asyncio.sleep(5)  # Non-blocking
```

### Pattern 4: File I/O in Async Functions

**Before** (Blocking):
```python
async def read_file():
    with open("data.txt") as f:
        return f.read()  # Blocks!
```

**After** (Non-blocking):
```python
from src.utils.async_io import run_in_executor

async def read_file():
    def _sync_read():
        with open("data.txt") as f:
            return f.read()
    
    return await run_in_executor(_sync_read)
```

## Migration Guide

### Step 1: Identify Async/Sync Mismatches

Look for these patterns:
- `requests.get/post` in `async def` functions
- `sqlite3.connect` in `async def` functions
- `time.sleep` in `async def` functions
- File I/O (`open`, `read`, `write`) in `async def` functions
- Missing `await` on async calls

### Step 2: Import Async Utilities

```python
from src.utils.async_io import (
    async_http_get,
    async_http_post,
    async_sqlite_connect,
    run_in_executor,
    sync_to_async,
)
```

### Step 3: Replace Sync Operations

Replace sync blocking operations with async equivalents:

1. **HTTP**: `requests.get()` → `await async_http_get()`
2. **SQLite**: `sqlite3.connect()` → `async with async_sqlite_connect()`
3. **Sleep**: `time.sleep()` → `await asyncio.sleep()`
4. **File I/O**: Wrap in `await run_in_executor()`

### Step 4: Test Async Flow

Ensure:
- No blocking operations in async functions
- All async operations are awaited
- Proper error handling
- Timeout management where needed

## Recommended Dependencies

For best performance, install native async libraries:

```bash
pip install aiohttp aiosqlite
```

These provide true async I/O instead of executor wrappers.

## Performance Considerations

### Executor vs Native Async

- **Executor (current fallback)**: Sync operations run in thread pool
  - Pros: Works with existing sync code
  - Cons: Context switching overhead, limited scalability
  
- **Native Async (aiohttp/aiosqlite)**: True async I/O
  - Pros: Better performance, true concurrency
  - Cons: Requires async-compatible libraries

### Best Practices

1. **Use native async** when possible (aiohttp, aiosqlite)
2. **Use executor** for legacy sync code that can't be changed
3. **Batch operations** when using executor to reduce overhead
4. **Set timeouts** on all async operations
5. **Use cancellation tokens** for long-running operations

## Code Examples

### Example: Async HTTP API Client

```python
from src.utils.async_io import async_http_get, async_http_post
from src.utils.timeout_manager import get_timeout_manager

class AsyncAPIClient:
    async def get_user(self, user_id: str):
        timeout_manager = get_timeout_manager()
        
        response = await timeout_manager.async_timeout(
            async_http_get,
            timeout=30.0,
            operation_name=f"get_user_{user_id}",
            url=f"https://api.example.com/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response['status'] == 200:
            return response['data']
        else:
            raise Exception(f"API error: {response['status']}")
```

### Example: Async Database Operations

```python
from src.utils.async_io import async_sqlite_connect
from src.utils.cancellation_token import get_cancellation_token

async def get_unanalyzed_posts(limit: int = 100):
    token = get_cancellation_token()
    token.check_cancellation()  # Raise if cancelled
    
    async with async_sqlite_connect("beyondlines.db") as conn:
        cursor = await conn.execute(
            "SELECT * FROM posts WHERE analyzed_at IS NULL LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return rows
```

### Example: Batch Operations

```python
import asyncio
from src.utils.async_io import run_in_executor

async def batch_process_items(items):
    # Process in batches to avoid overwhelming executor
    batch_size = 10
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        tasks = [run_in_executor(process_item, item) for item in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
    
    return results
```

## Current Status

✅ **Infrastructure Complete**:
- Async I/O utilities created
- HTTP async wrapper (aiohttp or executor fallback)
- SQLite async wrapper (aiosqlite or executor fallback)
- Executor utilities for legacy sync code
- Sync-to-async decorator

📋 **Remaining Work**:
1. Audit codebase for async/sync mismatches
2. Migrate critical paths to async I/O utilities
3. Add `aiohttp` and `aiosqlite` to requirements
4. Test async performance improvements
5. Document async patterns in specific modules

## Files Created

- `src/utils/async_io.py` - Async I/O utilities and wrappers
- `docs/ASYNC_SYNC_MISMATCH_FIXES.md` - This document

## Next Steps

1. **Install async dependencies**:
   ```bash
   pip install aiohttp aiosqlite
   ```

2. **Identify critical async paths**:
   - Collection services
   - Analysis pipelines
   - Publishing workflows
   - Database operations

3. **Migrate incrementally**:
   - Start with high-traffic paths
   - Use async I/O utilities
   - Add proper error handling
   - Add timeout management

4. **Monitor performance**:
   - Measure before/after
   - Identify bottlenecks
   - Optimize based on metrics

## Summary

✅ **Async/Sync Mismatch Infrastructure**: Complete
- Created comprehensive async I/O utilities
- Support for HTTP, SQLite, file I/O
- Executor fallback for legacy code
- Clear patterns and examples

📋 **Migration**: Remaining
- Audit codebase for mismatches
- Migrate critical paths
- Test and optimize

The infrastructure is now in place to properly handle async/sync operations across the codebase.






