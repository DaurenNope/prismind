# Twitter API Credentials Setup

## Credentials You Have

✅ **API Key**: `KtO2WhsfJyzsxydCAnaHLmIP0`
✅ **API Key Secret**: `XGMMJDLtxfQivMg7JF7JN6sYozb28fin9lRjYgq9SJSkeCVb55`
✅ **Bearer Token**: `AAAAAAAAAAAAAAAAAAAAAMmT4QEAAAAAJpvPab%2F4zgvKLuG673NOF6Iw9dM%3Dz0VZjx0myVymVs4z9WY5QZPSD5sH2w06mx8d9azCDUY2OctAkb`

## Missing Credentials (Required for Posting)

❌ **Access Token** - Need to generate
❌ **Access Token Secret** - Need to generate

## How to Get Access Token & Secret

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Click on your app (the one with API Key `KtO2WhsfJyzsxydCAnaHLmIP0`)
3. Go to **"Keys and tokens"** tab
4. Under **"Access Token and Secret"**, click **"Generate"**
5. Copy both values:
   - Access Token
   - Access Token Secret

## Add to .env File

Add these lines to your `.env` file:

```bash
# Twitter API v2 Credentials
TWITTER_API_KEY=KtO2WhsfJyzsxydCAnaHLmIP0
TWITTER_API_SECRET=XGMMJDLtxfQivMg7JF7JN6sYozb28fin9lRjYgq9SJSkeCVb55
TWITTER_ACCESS_TOKEN=YOUR_ACCESS_TOKEN_HERE
TWITTER_ACCESS_TOKEN_SECRET=YOUR_ACCESS_TOKEN_SECRET_HERE
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAMmT4QEAAAAAJpvPab%2F4zgvKLuG673NOF6Iw9dM%3Dz0VZjx0myVymVs4z9WY5QZPSD5sH2w06mx8d9azCDUY2OctAkb
```

## Test the Credentials

After adding all credentials, run:

```bash
python scripts/test_twitter_api.py
```

This will verify:
- ✅ Authentication works
- ✅ You can post tweets
- ✅ Rate limits are accessible

## Important Notes

- **Bearer Token** is read-only (can read tweets, but not post)
- **Access Token + Secret** are needed for posting tweets
- Keep these credentials **secret** - never commit to git
- If you regenerate tokens, update `.env` immediately
