# Threads Authentication Issue - Cookies Expired

## Problem

**Error**: "Could not log you in now. Please try again later."

**Cause**: The Threads cookies in `config/threads_cookies.json` are expired or invalid. Only 2 cookies present (should be 10+).

**Why it's not headless**: The extractor opens a visible browser because it's trying to log in (cookies failed).

## Solution: Refresh Your Cookies

### Option 1: Quick Refresh (Recommended)

Run the refresh script I just created:

```bash
python3 refresh_threads_cookies.py
```

This will:
1. Open a browser window
2. Navigate to Threads login
3. You log in manually (with your Instagram/Threads account)
4. Save the fresh cookies automatically
5. Close the browser

**Then** you can collect:
```bash
python3 collect_threads_now.py
```

### Option 2: Manual Cookie Export

If the script doesn't work, you can manually export cookies:

1. Open Chrome/Edge
2. Go to https://www.threads.net and log in
3. Install "EditThisCookie" extension
4. Export cookies as JSON
5. Save to `config/threads_cookies.json`

## Why Cookies Expire

Threads/Instagram cookies typically expire:
- After 30-90 days of inactivity
- If you log out on the main site
- If Instagram detects suspicious activity
- After password changes

## Current Cookie Status

```
File: config/threads_cookies.json
Modified: 2025-10-14 17:10:44
Cookies: 2 (⚠️  Too few - expired/invalid)
Expected: 10-15 cookies for valid session
```

## How Collection Works

```
Collection Attempt
      ↓
Try Cookie Auth (headless=True)
      ↓
   Success? ──Yes──> Collect posts ✅
      ↓ No
Open Browser (headless=False)
      ↓
Manual Login Required
      ↓
User aborts → Error ❌
```

## After You Refresh Cookies

The collection will work **completely headless** again:
- No browser windows
- Fast authentication
- Automatic collection
- Works in background

## Quick Fix Right Now

```bash
# 1. Refresh cookies (opens browser for you to log in)
python3 refresh_threads_cookies.py

# 2. After successful login, collect normally
python3 collect_threads_now.py

# Or use Svelte UI
# Just go to Collection tab and click "Collect from Threads"
```

## Future Prevention

To avoid cookie expiration:
- Collect from Threads at least once a week
- Don't log out from Threads website
- Keep the same device/browser
- The refresh script creates new cookies when needed

## Summary

**Current State**: Cookies expired → login fails → browser opens (not headless)

**Solution**: Run `python3 refresh_threads_cookies.py` → log in once → cookies saved → future collections work headless

**After Fix**: All collections work headless again, no browser windows! ✅
