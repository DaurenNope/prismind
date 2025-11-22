# Twitter API Setup Guide

Since you can get Twitter API keys, we're switching from browser automation to the official Twitter API v2. This is more reliable and handles rate limits automatically.

## Rate Limits

Twitter API v2 has these rate limits:
- **Posting tweets**: 300 tweets per 15 minutes (per user)
- **Reading tweets**: 300 requests per 15 minutes
- **User lookup**: 300 requests per 15 minutes

Our implementation uses Tweepy's built-in rate limiting (`wait_on_rate_limit=True`), which automatically waits when limits are hit.

## Setup Steps

### 1. Get Twitter API Keys

1. Go to https://developer.twitter.com
2. Apply for a Developer account (if you don't have one)
3. Create a new App/Project
4. Get these credentials:
   - **API Key** (Consumer Key)
   - **API Secret** (Consumer Secret)
   - **Access Token**
   - **Access Token Secret**

### 2. Add to `.env`

Add these to your `.env` file:

```bash
# Twitter API v2 Credentials
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

### 3. Install Dependencies

```bash
pip install tweepy==4.14.0
```

Or if using the full requirements:

```bash
pip install -r requirements.txt
```

### 4. Test the Connection

You can test if the API keys work:

```python
from src.publishing.platforms.twitter import TwitterPoster

poster = TwitterPoster()
print(f"✅ Authenticated as @{poster.username}")
```

## How It Works

### Rate Limiting

The `TwitterPoster` class uses Tweepy's built-in rate limiting:
- Automatically waits when rate limits are hit
- Logs when it's waiting
- Retries automatically after the limit resets

### Posting Tweets

```python
from src.publishing.platforms.twitter import post_to_twitter_direct

result = post_to_twitter_direct("Hello, world!")
if result["success"]:
    print(f"Posted: {result['url']}")
else:
    print(f"Error: {result['error']}")
```

### Posting Threads

```python
from src.publishing.platforms.twitter import TwitterPoster

poster = TwitterPoster()
result = poster.post_thread([
    "First tweet in thread",
    "Second tweet",
    "Third tweet"
])
```

## Migration from Browser Automation

The publishing worker (`src/publishing/worker.py`) will automatically use the API client instead of browser automation when API keys are present.

**Browser automation is still used for:**
- Reading bookmarks (no API endpoint for this)
- Collection/scraping (if needed)

**API is used for:**
- Posting tweets ✅
- Posting threads ✅
- Replying to tweets ✅

## Troubleshooting

### "Twitter credentials missing in .env"
- Make sure all 4 credentials are in `.env`
- Check for typos in variable names

### Rate Limit Errors
- Tweepy should auto-wait, but if you see errors:
  - Check your rate limit status
  - Space out posts more (e.g., 1 per minute max)
  - Consider upgrading to Twitter API Pro ($100/month for higher limits)

### Authentication Errors
- Verify credentials are correct
- Check if your Developer account is approved
- Make sure your app has "Read and Write" permissions

## Benefits Over Browser Automation

✅ **More reliable** - No browser detection issues
✅ **Faster** - Direct API calls vs browser automation
✅ **Rate limit handling** - Automatic backoff
✅ **Official support** - Twitter's official API
✅ **Better error messages** - Clear API error codes

## Next Steps

1. Get your API keys from Twitter Developer Portal
2. Add them to `.env`
3. Test with a simple post
4. The publishing worker will automatically use the API

Once this is working, we can remove the browser automation code for posting (but keep it for bookmark reading if needed).
