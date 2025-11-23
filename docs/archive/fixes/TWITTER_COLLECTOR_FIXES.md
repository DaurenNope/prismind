# Twitter Collector Fixes

## Issues Fixed

### 1. Bookmark Validation ✅

**Problem**: Twitter collector was collecting tweets that weren't actually bookmarked, just because they appeared on the bookmarks page.

**Solution**: Added comprehensive bookmark verification before extracting each tweet:

```python
# Method 1: Check for aria-pressed="true" on bookmark button
bookmark_button = await tweet_element.query_selector('[data-testid="bookmark"]')
if bookmark_button:
    aria_pressed = await bookmark_button.get_attribute("aria-pressed")
    if aria_pressed == "true":
        is_bookmarked = True

# Method 2: Check button text/label for "Remove" or "Saved"
if not is_bookmarked:
    button_text = await bookmark_button.inner_text()
    aria_label = await bookmark_button.get_attribute("aria-label") or ""
    if any(keyword in button_text.lower() or keyword in aria_label.lower()
           for keyword in ["remove", "saved", "bookmarked"]):
        is_bookmarked = True

# Method 3: Fallback text check
if not is_bookmarked:
    tweet_text = await tweet_element.inner_text()
    if "remove bookmark" in tweet_text.lower() or "saved" in tweet_text.lower():
        is_bookmarked = True
```

**Location**: `src/core/extraction/twitter_extractor_playwright.py` lines 703-743

### 2. URL Guard Enhancement ✅

**Problem**: Need better verification that we're actually on the bookmarks page.

**Solution**: Enhanced URL verification with additional page indicator checks:

```python
# Verify URL contains "bookmarks"
if "bookmarks" not in current_url:
    print(f"❌ CRITICAL: Not on bookmarks page! Current URL: {current_url}")
    return []

# Additional verification: Check for bookmarks page indicator
bookmarks_indicator = await self.page.query_selector(
    'h1:has-text("Bookmarks"), [data-testid="primaryColumn"] h1, [aria-label*="Bookmarks"]'
)
```

**Location**: `src/core/extraction/twitter_extractor_playwright.py` lines 631-654

## How It Works Now

1. **Navigate to bookmarks page**: `https://x.com/i/bookmarks`
2. **Verify URL**: Check that URL contains "bookmarks"
3. **Verify page indicator**: Check for bookmarks page header/title
4. **For each tweet**:
   - Verify bookmark button has `aria-pressed="true"`
   - OR verify button text/label contains "Remove", "Saved", or "Bookmarked"
   - Skip tweet if bookmark status cannot be verified
5. **Extract only verified bookmarked tweets**

## Safety Features

- **Triple verification**: aria-pressed, button label, and text fallback
- **Fail-safe**: If bookmark status cannot be verified, skip the tweet
- **URL guard**: Abort if not on bookmarks page
- **Logging**: Clear messages about what's being verified

## Testing

To test the fixes:

1. Run Twitter collector:
   ```bash
   python -m src.pipeline.orchestrator collect_platform twitter
   ```

2. Check logs for:
   - `✅ Verified on bookmarks page`
   - `✅ Tweet X: Verified bookmark (aria-pressed=true)`
   - `⏭️ Skipping tweet X: Not bookmarked`

3. Verify collected posts are actually bookmarked in your Twitter account

## Known Limitations

- **Bookmarks page only**: Currently only collects from `/i/bookmarks`
- **No API alternative**: Browser automation required (API has very limited bookmark access on Free tier)
- **Rate limits**: Free tier bookmark API: 1 request per 15 minutes (very restrictive)

## Future Improvements

1. **Use Twitter API for bookmarks** (if upgraded to Basic/Pro tier):
   - `GET /2/users/:id/bookmarks` endpoint
   - Better rate limits (10 requests/15min on Basic tier)

2. **Hybrid approach**:
   - Use API when available
   - Fallback to browser automation for Free tier

3. **Better error handling**:
   - Retry logic for failed bookmark verifications
   - Screenshot on verification failures for debugging
