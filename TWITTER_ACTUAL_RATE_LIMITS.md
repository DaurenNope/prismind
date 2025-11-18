# Twitter API v2 Actual Rate Limits

## Critical: Free Tier Posting Limits

### POST /2/tweets (Posting Tweets)

**Free Tier:**
- **17 tweets per 24 hours** (PER USER)
- **17 tweets per 24 hours** (PER APP)

**Basic Tier:**
- 100 requests / 24 hours (PER USER)
- 1,667 requests / 24 hours (PER APP)

**Pro Tier ($100/month):**
- 100 requests / 15 mins (PER USER)
- 10,000 requests / 24 hours (PER APP)

## Your Current Limits (Free Tier)

### Posting
- ✅ **17 tweets per day** (24-hour window)
- ⚠️ This is a hard limit - very restrictive!

### Reading Bookmarks
- **GET /2/users/:id/bookmarks**: 1 request / 15 mins (PER USER)
- This is why browser automation for bookmarks might be necessary

### Other Important Limits (Free Tier)

**Reading Tweets:**
- GET /2/tweets/:id: 1 request / 15 mins (PER USER)
- GET /2/tweets: 1 request / 15 mins (PER USER)

**User Lookup:**
- GET /2/users/:id: 1 request / 24 hours (PER USER)
- GET /2/users/me: 25 requests / 24 hours (PER USER)

**Search:**
- GET /2/tweets/search/recent: 1 request / 15 mins (PER USER)

## Rate Limit Headers

Twitter API returns these headers with every response:
- `x-rate-limit-limit`: Rate limit ceiling for the endpoint
- `x-rate-limit-remaining`: Remaining requests for the 15-minute window
- `x-rate-limit-reset`: Remaining time before the rate limit resets (UTC epoch seconds)

## Error Handling

When rate limit is exceeded:
- HTTP 429 "Too Many Requests"
- Error code: 88
- Message: "Rate limit exceeded"

## Recommendations

### For Free Tier (17 tweets/day):

1. **Space out posts**: Maximum 17 posts per day
2. **Prioritize quality**: With only 17 posts/day, make each one count
3. **Schedule carefully**: Use the publishing scheduler to space posts throughout the day
4. **Monitor usage**: Track how many tweets you've posted today

### Upgrade Considerations:

**Basic Tier** ($100/month):
- 100 tweets/day (PER USER)
- Better for moderate posting

**Pro Tier** ($100/month):
- 100 tweets per 15 minutes (PER USER)
- 10,000 tweets per day (PER APP)
- Best for high-volume posting

### For Bookmarks Collection:

Since `GET /2/users/:id/bookmarks` is only **1 request per 15 minutes** on Free tier:
- Browser automation might still be necessary for bookmark collection
- Or upgrade to Basic/Pro tier for better bookmark API access

## Implementation Notes

Our `TwitterPoster` class uses:
- `wait_on_rate_limit=True` - Automatically waits when limits are hit
- Tweepy handles the 429 errors and waits until reset

But with only 17 tweets/day, you need to:
1. Track daily usage
2. Prevent posting if daily limit is reached
3. Queue posts for the next day if limit is hit

## Daily Limit Tracking

We should add:
- Daily tweet counter
- Check before posting: "Have we posted 17 tweets today?"
- Queue excess posts for tomorrow
