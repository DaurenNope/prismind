# Add Twitter Credentials to .env

## What You Have ✅

You provided:
- **API Key**: `KtO2WhsfJyzsxydCAnaHLmIP0`
- **API Key Secret**: `XGMMJDLtxfQivMg7JF7JN6sYozb28fin9lRjYgq9SJSkeCVb55`
- **Bearer Token**: `AAAAAAAAAAAAAAAAAAAAAMmT4QEAAAAAJpvPab%2F4zgvKLuG673NOF6Iw9dM%3Dz0VZjx0myVymVs4z9WY5QZPSD5sH2w06mx8d9azCDUY2OctAkb`

## What You Need ❌

- **Access Token** (generate from Twitter Developer Portal)
- **Access Token Secret** (generate from Twitter Developer Portal)

## How to Get Access Token & Secret

1. **Go to**: https://developer.twitter.com/en/portal/dashboard
2. **Click** on your app (the one with API Key `KtO2WhsfJyzsxydCAnaHLmIP0`)
3. **Click** the **"Keys and tokens"** tab
4. **Scroll** to **"Access Token and Secret"** section
5. **Click** **"Generate"** button
6. **Copy** both values:
   - Access Token (starts with numbers)
   - Access Token Secret (long string)

## Add to .env File

Open your `.env` file and add these lines:

```bash
# Twitter API v2 Credentials
TWITTER_API_KEY=KtO2WhsfJyzsxydCAnaHLmIP0
TWITTER_API_SECRET=XGMMJDLtxfQivMg7JF7JN6sYozb28fin9lRjYgq9SJSkeCVb55
TWITTER_ACCESS_TOKEN=PASTE_YOUR_ACCESS_TOKEN_HERE
TWITTER_ACCESS_TOKEN_SECRET=PASTE_YOUR_ACCESS_TOKEN_SECRET_HERE
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAMmT4QEAAAAAJpvPab%2F4zgvKLuG673NOF6Iw9dM%3Dz0VZjx0myVymVs4z9WY5QZPSD5sH2w06mx8d9azCDUY2OctAkb
```

## Test After Adding

Once you've added the Access Token and Secret, run:

```bash
python scripts/test_twitter_api.py
```

This will verify everything works and you can post tweets.

## Important Notes

- **Bearer Token** = Read-only (can read tweets, but not post)
- **Access Token + Secret** = Required for posting tweets
- Keep these **secret** - never commit to git
- If you regenerate tokens, update `.env` immediately
