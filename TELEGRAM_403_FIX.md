# Telegram 403 Error Fix

## Problem

The publisher worker was repeatedly retrying Telegram posts that failed with HTTP 403 (Forbidden) errors. This created an infinite retry loop where the same post was attempted every 15 seconds, flooding the logs with error messages.

## Root Cause

- HTTP 403 is a **permanent failure** (Forbidden - typically means invalid bot token, missing permissions, or chat access denied)
- The worker was marking all failures as "retry" status, causing infinite retries
- No distinction between permanent failures (400, 401, 403) and transient failures (500, 502, 503, timeout)
- No retry count tracking to prevent infinite retries

## Solution

### 1. Detect Permanent vs Transient Failures

**Permanent Failures** (marked as "failed" immediately):
- HTTP 400 (Bad Request)
- HTTP 401 (Unauthorized - invalid bot token)
- HTTP 403 (Forbidden - missing permissions or chat access)
- Configuration errors (missing bot token or chat_id)
- Message too long (exceeds 4096 chars)
- Telegram API errors containing: "forbidden", "unauthorized", "bad request", "chat not found", "bot blocked"

**Transient Failures** (retried with limit):
- HTTP 500, 502, 503 (server errors)
- Timeout errors
- Network errors
- Other exceptions

### 2. Retry Count Tracking

- Maximum retry attempts: **5**
- Each retry increments `retry_count`
- After 5 retries, post is marked as "failed"
- Retry count is stored in `scheduled_posts.retry_count` field

### 3. Better Error Messages

- Added context to error messages:
  - `HTTP error: 403 (Forbidden - check bot token permissions or chat access)`
  - `HTTP error: 401 (Unauthorized - invalid bot token)`
  - `HTTP error: 400 (Bad Request - check message format or chat_id)`

### 4. Status Updates

- **Permanent failures**: Status set to `"failed"` immediately
- **Transient failures**: Status set to `"retry"` (up to 5 attempts)
- **Max retries exceeded**: Status set to `"failed"`
- **Error message**: Stored in `error_message` field for debugging

## Changes Made

### `src/publishing/worker.py`

1. **`post_to_telegram_direct()` function**:
   - Returns `permanent_failure` flag in result dict
   - Detects permanent failures from HTTP status codes
   - Detects permanent failures from Telegram API error descriptions
   - Adds context to error messages

2. **`_run_loop()` method**:
   - Checks `permanent_failure` flag from result
   - Marks permanent failures as "failed" immediately
   - Tracks retry count for transient failures
   - Marks as "failed" after max retries (5)
   - Stores error messages in `error_message` field

## Impact

**Before**:
- ❌ Infinite retry loop for 403 errors
- ❌ Logs flooded with error messages every 15 seconds
- ❌ No distinction between permanent and transient failures
- ❌ No retry limit

**After**:
- ✅ Permanent failures (403, 401, 400) marked as "failed" immediately
- ✅ Transient failures retried up to 5 times
- ✅ Clear error messages with context
- ✅ No infinite retry loops
- ✅ Retry count tracking

## Testing

To test the fix:

1. **Permanent failure test**:
   - Set invalid `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID`
   - Schedule a post
   - Verify it's marked as "failed" immediately (not "retry")

2. **Transient failure test**:
   - Temporarily block network access
   - Schedule a post
   - Verify it retries up to 5 times, then marks as "failed"

3. **403 error test**:
   - Use a bot token without permissions
   - Schedule a post
   - Verify it's marked as "failed" immediately with clear error message

## Database Schema

The `scheduled_posts` table should have:
- `status` field: `"pending"`, `"retry"`, `"failed"`, `"posted"`
- `retry_count` field: Integer (default 0)
- `error_message` field: Text (optional, for storing error details)

If these fields don't exist, you may need to add them via migration.

