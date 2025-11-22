# Twitter API Rate Limits - Summary

## ⚠️ Critical: Free Tier is Very Restrictive

### Posting Limits (POST /2/tweets)

| Tier | Limit | Window |
|------|-------|--------|
| **Free** | **17 tweets** | **24 hours** |
| Basic | 100 tweets | 24 hours |
| Pro ($100/mo) | 100 tweets | 15 minutes |

**Your account is on Free tier = 17 tweets per day maximum!**

## What We've Implemented

### 1. Daily Rate Limiter (`src/publishing/twitter_rate_limiter.py`)
- Tracks daily tweet count
- Prevents posting when limit is reached
- Automatically resets at midnight
- Persists state to `.twitter_rate_limit_state.json`

### 2. Publishing Worker Integration
- Checks limit before posting
- Reschedules posts for tomorrow if limit reached
- Records each successful post

### 3. Configuration

Set your tier in `.env`:
```bash
TWITTER_API_TIER=free  # or "basic" or "pro"
```

## How It Works

1. **Before posting**: Worker checks `can_post()`
2. **If limit reached**: Post is rescheduled for tomorrow
3. **After posting**: `record_post()` increments counter
4. **Daily reset**: Counter resets at midnight

## Status Check

You can check your current status:
```python
from src.publishing.twitter_rate_limiter import get_twitter_limiter
limiter = get_twitter_limiter()
status = limiter.get_status()
print(f"Used: {status['used']}/{status['limit']}")
print(f"Remaining: {status['remaining']}")
```

## Recommendations

### For Free Tier (17 tweets/day):

1. **Prioritize quality**: Make each tweet count
2. **Space throughout day**: Don't post all 17 at once
3. **Monitor usage**: Check status regularly
4. **Consider upgrade**: If you need more than 17/day

### Upgrade Path:

- **Basic Tier**: 100 tweets/day (better for moderate use)
- **Pro Tier**: 100 tweets per 15 minutes (for high-volume)

## Important Notes

- Limits are **per user** (OAuth 1.0a User Context)
- 24-hour window is **rolling** (not calendar day)
- Our limiter uses calendar day for simplicity
- Tweepy handles 429 errors automatically

## Bookmarks Collection

**GET /2/users/:id/bookmarks**: Only **1 request per 15 minutes** on Free tier

This is why browser automation for bookmarks might still be necessary, or upgrade to Basic/Pro for better API access.
