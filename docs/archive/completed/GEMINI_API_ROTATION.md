# Gemini API Key Rotation

## Overview

The rewriter supports rotating between multiple Gemini API keys to avoid rate limits during high-volume content generation.

## Rate Limits (Free Tier)

Different Gemini models have different limits:

| Model | RPM (Requests/Min) | RPD (Requests/Day) | TPM (Tokens/Min) |
|-------|-------------------|-------------------|------------------|
| gemini-2.0-flash | 15 | 200 | 1M |
| gemini-2.0-flash-exp | 10 | 50 | 250K |
| gemini-2.5-flash | 10 | 250 | 250K |
| gemini-2.5-pro | 2 | 50 | 125K |

## Setup

### Single API Key

Add to your `.env` file:

```bash
GEMINI_API_KEY=your_api_key_here
```

### Multiple API Keys (Rotation)

To enable rotation, add multiple keys using this format:

```bash
# Primary key (used first)
GEMINI_API_KEY=AIza...key1

# Additional keys for rotation
GEMINI_API_KEY_1=AIza...key2
GEMINI_API_KEY_2=AIza...key3
GEMINI_API_KEY_3=AIza...key4
```

The system will:
1. Load all available keys at startup
2. Use them in round-robin rotation
3. If a key hits rate limit (HTTP 429 or 403), automatically try the next key
4. Log which key number is being used for each request

## How It Works

```python
# ContentRewriter automatically loads all keys
rewriter = ContentRewriter()
# Logs: "✅ Loaded 3 Gemini API key(s) for rotation"

# Each request uses next key in rotation
result = await rewriter.rewrite_analyzed_post(...)
# Logs: "📡 Trying API key #1/3"
# Logs: "✅ Gemini (key #1) generated 500 chars"

# Next request uses key #2, then #3, then back to #1
```

## Rate Limit Handling

When a key hits rate limit:

```
⚠️ API key #1 hit rate limit, trying next key...
📡 Trying API key #2/3
✅ Gemini (key #2) generated 450 chars
```

If all keys are exhausted:

```
❌ All 3 API keys failed. Last error: Rate limit on key #3
```

## Testing

Test the rotation system:

```bash
python test_api_rotation.py
```

Test with multiple rewrites:

```bash
python test_10_rewrites.py
```

## Best Practices

1. **For Development**: 1 key is usually enough
2. **For Bulk Processing**: Use 3-5 keys to handle 10-20 posts without waiting
3. **Production**: Monitor usage at https://aistudio.google.com/app/apikey and add keys as needed

## Getting More API Keys

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Select your Google Cloud project
4. Copy the key and add to `.env`

Each Google account can have multiple API keys, each with their own rate limits.

## Current Model

The rewriter uses `gemini-2.0-flash-exp` by default. To change:

Edit `src/publishing/rewriter.py`:

```python
self.gemini_model = "gemini-2.5-flash"  # or other model
```
