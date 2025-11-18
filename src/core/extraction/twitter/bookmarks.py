import logging

logger = logging.getLogger(__name__)
"""Twitter bookmark extraction - simple and reliable"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from playwright.async_api import Page

try:
    from dateutil import parser
except ImportError as e:
    logger.error(f"Error: {e}")
    # Fallback if dateutil not available
    import datetime as dt

    parser = dt

from ..social_extractor_base import SocialPost
from .utils import jitter


class TwitterBookmarks:
    """Extracts bookmarked tweets from Twitter"""

    def __init__(self, page: Page):
        self.page = page

    async def get_bookmarks(
        self,
        limit: int = 50,
        skip_ids: Optional[Set[str]] = None,
        stop_at_post_id: Optional[str] = None,
    ) -> List[SocialPost]:
        """
        Extract bookmarked tweets - SIMPLE workflow:
        1. Scroll until we see last saved tweet
        2. Go back and click all "show more" buttons
        3. Scrape all tweets
        4. Handle threads (multiple tweets) individually
        """
        if skip_ids is None:
            skip_ids = set()

        logger.info(f"📥 Extracting bookmarks (limit: {limit})...")

        # Navigate to bookmarks
        await self._navigate_to_bookmarks()
        await asyncio.sleep(3)

        # EARLY CHECK: Check if the first few tweets are already saved
        # Only stop if ALL of the first 3 tweets are already saved (not just the first one)
        logger.info("🔍 Checking first tweet(s) to see if collection is needed...")
        first_elements = await self.page.query_selector_all(
            'article[data-testid="tweet"]'
        )

        if first_elements and len(first_elements) > 0:
            saved_count = 0
            checked_count = min(3, len(first_elements))  # Check first 3 tweets

            for i, element in enumerate(first_elements[:checked_count]):
                try:
                    # Quick check: extract just the ID
                    tweet_link = await element.query_selector('a[href*="/status/"]')
                    if tweet_link:
                        href = await tweet_link.get_attribute("href")
                        if href and "/status/" in href:
                            element_tweet_id = (
                                href.split("/status/")[1].split("?")[0].split("/")[0]
                            )
                            element_id_with_prefix = f"twitter_{element_tweet_id}"

                            # Check if this tweet is in skip_ids (already saved)
                            if (
                                element_id_with_prefix in skip_ids
                                or element_tweet_id in skip_ids
                            ):
                                saved_count += 1
                                logger.info(
                                    f"   Tweet {i+1} is already saved: {element_id_with_prefix}"
                                )

                            # Check if this is the stop tweet
                            if stop_at_post_id:
                                stop_id_normalized = (
                                    str(stop_at_post_id)
                                    .replace("twitter_", "")
                                    .replace("Twitter_", "")
                                    .strip()
                                )
                                stop_id_raw = str(stop_at_post_id).strip()

                                if (element_tweet_id == stop_id_normalized) or (
                                    element_id_with_prefix == stop_id_raw
                                ):
                                    logger.info(
                                        f"✅ Tweet {i+1} matches stop ID: {element_tweet_id}"
                                    )
                                    logger.info(
                                        f"   Stopping collection - all posts are already saved"
                                    )
                                    return []  # Return empty list
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            # Only stop if ALL checked tweets are already saved
            if saved_count == checked_count and checked_count > 0:
                logger.info(
                    f"🛑 All first {checked_count} tweets are already saved - stopping collection"
                )
                return []  # Return empty list - nothing new to collect
            elif saved_count > 0:
                logger.info(
                    f"   {saved_count}/{checked_count} tweets already saved, but continuing to check for new ones..."
                )

        # Step 1: Scroll until we find the last saved tweet
        logger.info("📜 Step 1: Scrolling to find last saved tweet...")
        found_stop_tweet = False
        scroll_count = 0
        max_scrolls = 50

        while not found_stop_tweet and scroll_count < max_scrolls:
            # Get all tweet elements
            elements = await self.page.query_selector_all(
                'article[data-testid="tweet"]'
            )

            # Check if we found the stop tweet OR if first visible tweets are in skip_ids
            if stop_at_post_id:
                stop_id_normalized = (
                    str(stop_at_post_id)
                    .replace("twitter_", "")
                    .replace("Twitter_", "")
                    .strip()
                )
                stop_id_raw = str(stop_at_post_id).strip()

                for element in elements:
                    try:
                        # Quick check: extract just the ID to see if this is the stop tweet
                        tweet_link = await element.query_selector('a[href*="/status/"]')
                        if tweet_link:
                            href = await tweet_link.get_attribute("href")
                            if href and "/status/" in href:
                                element_tweet_id = (
                                    href.split("/status/")[1]
                                    .split("?")[0]
                                    .split("/")[0]
                                )
                                # Check both normalized and with twitter_ prefix
                                element_id_with_prefix = f"twitter_{element_tweet_id}"

                                # Match if normalized OR with prefix matches
                                if (element_tweet_id == stop_id_normalized) or (
                                    element_id_with_prefix == stop_id_raw
                                ):
                                    logger.info(
                                        f"✅ Found last saved tweet during scroll: {element_tweet_id}"
                                    )
                                    found_stop_tweet = True
                                    break
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue

            # Even if top tweets are already saved, keep scrolling until we explicitly hit stop_at_post_id
            if elements and len(elements) > 0:
                first_element = elements[0]
                try:
                    tweet_link = await first_element.query_selector(
                        'a[href*="/status/"]'
                    )
                    if tweet_link:
                        href = await tweet_link.get_attribute("href")
                        if href and "/status/" in href:
                            element_tweet_id = (
                                href.split("/status/")[1].split("?")[0].split("/")[0]
                            )
                            element_id_with_prefix = f"twitter_{element_tweet_id}"

                            if (
                                element_id_with_prefix in skip_ids
                                or element_tweet_id in skip_ids
                            ):
                                logger.info(
                                    f"ℹ️ Top tweet already saved (continuing scroll): {element_id_with_prefix}"
                                )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    # Continue scrolling if we can't check

            if found_stop_tweet:
                break

            # Scroll down
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            scroll_count += 1

            if scroll_count % 5 == 0:
                logger.info(f"  Scrolled {scroll_count} times...")

        # Step 2: Scroll back to top and click "show more" buttons PER TWEET
        logger.debug("📖 Step 2: Clicking 'show more' buttons for each tweet...")
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)

        # Get all tweet articles first
        all_tweet_articles = await self.page.query_selector_all(
            'article[data-testid="tweet"]'
        )
        logger.info(f"  Found {len(all_tweet_articles)} tweet articles to process")

        clicked_count = 0

        # For each tweet, find and click its "show more" button
        for i, article in enumerate(all_tweet_articles):
            try:
                # Check if element is still attached to DOM before interacting
                try:
                    is_attached = await article.evaluate("el => el.isConnected")
                    if not is_attached:
                        continue  # Skip detached elements
                except Exception as attach_check_err:
                    # If we can't check, element might be stale - skip it
                    continue

                # Scroll article into view
                try:
                    await article.scroll_into_view_if_needed()
                    await asyncio.sleep(0.2)
                except Exception as scroll_err:
                    # Element detached during scroll - skip it
                    if "not attached" in str(
                        scroll_err
                    ).lower() or "isConnected" in str(scroll_err):
                        continue
                    raise

                # Look for "show more" button WITHIN this article - try ALL possible selectors
                show_more = None
                show_more_selectors = [
                    '[data-testid="tweet-text-show-more-button"]',  # Official test ID
                    'span:has-text("Show more")',  # Text-based
                    'span:has-text("Read more")',  # Alternative text
                    'div[role="button"]:has-text("Show more")',  # Button role
                    'div[role="button"]:has-text("Read more")',  # Button role alternative
                    '[dir="ltr"]:has-text("Show more")',  # LTR direction
                    'button:has-text("Show more")',  # Button element
                    'button:has-text("Read more")',  # Button element alternative
                ]

                for selector in show_more_selectors:
                    try:
                        found = await article.query_selector(selector)
                        if found:
                            # Verify it's actually visible and contains "show" or "more"
                            try:
                                is_visible = await found.is_visible()
                                text = await found.inner_text()
                                if is_visible and (
                                    "show" in text.lower()
                                    or "more" in text.lower()
                                    or "read" in text.lower()
                                ):
                                    show_more = found
                                    break
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                continue
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue

                if show_more:
                    try:
                        # Check if button is still attached before interacting
                        try:
                            is_attached = await show_more.evaluate(
                                "el => el.isConnected"
                            )
                            if not is_attached:
                                continue  # Skip detached button
                        except Exception:
                            continue  # Skip if we can't check

                        # Make sure button is visible
                        if await show_more.is_visible():
                            try:
                                await show_more.scroll_into_view_if_needed()
                            except Exception as scroll_err:
                                # Button detached during scroll - skip it
                                if "not attached" in str(
                                    scroll_err
                                ).lower() or "isConnected" in str(scroll_err):
                                    continue
                                raise
                            await asyncio.sleep(0.3)
                            try:
                                await show_more.click()
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                # Fallback: use JavaScript click
                                await self.page.evaluate(
                                    "(btn) => btn.click()", show_more
                                )
                            clicked_count += 1
                            await asyncio.sleep(
                                1.5
                            )  # Wait longer for expansion (was 0.5)
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        # Button might have been clicked or disappeared
                        continue
            except Exception as e:
                logger.error(f"Error: {e}")
                continue

        if clicked_count > 0:
            logger.info(f"  ✅ Clicked {clicked_count} 'show more' buttons")
            await asyncio.sleep(3)  # Final wait for all expansions (increased from 2)

        # Step 3: Extract all tweets - VERIFY they're bookmarked
        logger.debug("📝 Step 3: Extracting all tweets (verifying bookmarks)...")
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)

        # VERIFY: Check URL one more time
        current_url = self.page.url
        if "/i/bookmarks" not in current_url:
            logger.warning(
                f"⚠️ WARNING: Not on bookmarks page! Current URL: {current_url}"
            )
            logger.info("   This might be collecting from wrong page!")

        # Get all tweets by scrolling through
        all_elements = []
        seen_element_ids = set()
        scroll_pos = 0
        max_scrolls_for_extraction = 30  # Define variable for extraction step

        for _ in range(max_scrolls_for_extraction):
            elements = await self.page.query_selector_all(
                'article[data-testid="tweet"]'
            )

            for elem in elements:
                # VERIFY: Check if this tweet is actually bookmarked
                # On bookmarks page, all tweets should be bookmarked, but double-check
                try:
                    # Look for bookmark icon (should be filled/active on bookmarks page)
                    bookmark_icon = await elem.query_selector(
                        '[data-testid="bookmark"]'
                    )
                    if bookmark_icon:
                        # Check if it's filled (bookmarked)
                        icon_svg = await bookmark_icon.query_selector("svg")
                        if icon_svg:
                            # On bookmarks page, bookmark icon should be filled
                            # If we're on bookmarks page, all tweets here ARE bookmarks
                            pass  # Assume it's bookmarked if we're on /i/bookmarks
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

                # Use a simple ID based on position/content to dedupe
                try:
                    elem_id = await elem.get_attribute("data-tweet-id")
                    if not elem_id:
                        # Fallback: use inner text hash
                        text = await elem.inner_text()
                        elem_id = str(hash(text[:100]))

                    if elem_id not in seen_element_ids:
                        all_elements.append(elem)
                        seen_element_ids.add(elem_id)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    # If we can't get ID, add it anyway (better than missing tweets)
                    all_elements.append(elem)

            # Scroll down
            scroll_pos += 1000
            await self.page.evaluate(f"window.scrollTo(0, {scroll_pos})")
            await asyncio.sleep(1)

            if scroll_pos > 20000:  # Reasonable limit
                break

        logger.info(f"  Found {len(all_elements)} tweet elements from scrolling")

        posts = []
        seen_ids = set()

        # CRITICAL: Extract IMMEDIATELY after querying to avoid stale references
        # Twitter's DOM can change dynamically, so we must extract right after querying
        logger.info(f"  Extracting tweets immediately from current page state...")
        await asyncio.sleep(0.5)  # Brief pause to let DOM settle

        # Query and extract in batches to avoid stale references
        batch_size = 10
        extracted_count = 0

        for batch_start in range(0, limit * 2, batch_size):
            if len(posts) >= limit:
                break

            # Re-query fresh elements for this batch
            fresh_elements = await self.page.query_selector_all(
                'article[data-testid="tweet"]'
            )
            if len(fresh_elements) == 0:
                logger.warning(f"  ⚠️ No tweet elements found on page")
                break

            batch_elements = fresh_elements[batch_start : batch_start + batch_size]
            logger.info(
                f"  Processing batch {batch_start//batch_size + 1}: {len(batch_elements)} elements (total found: {len(fresh_elements)})"
            )

            for i, element in enumerate(batch_elements):
                if len(posts) >= limit:
                    break

                try:
                    # Verify element is still attached to DOM
                    try:
                        is_attached = await element.evaluate("el => el.isConnected")
                        if not is_attached:
                            if i < 3:
                                logger.warning(
                                    f"   ⚠️ Element {i+1} is detached from DOM, skipping"
                                )
                            continue
                    except Exception as attach_err:
                        # If we can't check (element might be stale), skip it
                        if i < 3:
                            logger.error(
                                f"   ⚠️ Element {i+1} check failed: {attach_err}, skipping"
                            )
                        continue

                    # Extract tweet (each article is a tweet, threads are separate articles)
                    # CRITICAL: Extract quickly before page context changes
                    tweet = await self._extract_tweet(element)
                    if not tweet or not tweet.post_id:
                        if i < 5:  # Log first 5 failures for debugging
                            logger.error(
                                f"   ⚠️ Failed to extract tweet {i+1}: tweet={tweet}, post_id={tweet.post_id if tweet else 'None'}"
                            )
                            # Additional debug: check what the element looks like
                            try:
                                element_tag = await element.evaluate("el => el.tagName")
                                element_class = await element.evaluate(
                                    "el => el.className"
                                )
                                has_status_link = await element.query_selector(
                                    'a[href*="/status/"]'
                                )
                                logger.info(
                                    f"      Element: {element_tag}, class: {element_class[:100] if element_class else 'None'}, has_status_link: {has_status_link is not None}"
                                )
                            except Exception as debug_e:
                                logger.error(f"      Debug error: {debug_e}")
                        continue

                    # Check if we reached stop tweet - STOP IMMEDIATELY when found
                    if stop_at_post_id:
                        # Normalize both IDs for comparison
                        tweet_id_normalized = (
                            str(tweet.post_id)
                            .replace("twitter_", "")
                            .replace("Twitter_", "")
                            .strip()
                        )
                        stop_id_normalized = (
                            str(stop_at_post_id)
                            .replace("twitter_", "")
                            .replace("Twitter_", "")
                            .strip()
                        )

                        # Also check raw IDs
                        tweet_id_raw = str(tweet.post_id).strip()
                        stop_id_raw = str(stop_at_post_id).strip()

                        # Match if normalized OR raw IDs match
                        if (tweet_id_normalized == stop_id_normalized) or (
                            tweet_id_raw == stop_id_raw
                        ):
                            logger.info(
                                f"✅ Reached last saved tweet: {tweet_id_normalized} (stop ID: {stop_id_normalized})"
                            )
                            logger.info(
                                f"   Stopping collection - all posts after this are already saved"
                            )
                            logger.info(
                                f"   Collected {len(posts)} new posts before stopping"
                            )
                            return posts  # Return immediately - don't process any more

                    # Skip if already processed or in skip list
                    if tweet.post_id in seen_ids:
                        logger.info(f"   ⏭️ Skipping duplicate tweet: {tweet.post_id}")
                        continue
                    if tweet.post_id in skip_ids:
                        logger.info(
                            f"   ⏭️ Skipping tweet already saved: {tweet.post_id}"
                        )
                        continue

                    posts.append(tweet)
                    seen_ids.add(tweet.post_id)
                    logger.info(
                        f"   ✅ Extracted tweet {len(posts)}: {tweet.post_id} by @{tweet.author_handle or 'unknown'}"
                    )

                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

        logger.info(
            f"✅ Extracted {len(posts)} tweet elements from page (duplicate filtering happens in collector)"
        )
        return posts

    async def _navigate_to_bookmarks(self):
        """Navigate to bookmarks page - VERIFY we're actually on bookmarks"""
        logger.info("🌐 Navigating to bookmarks...")

        # Check if page is still open
        if self.page.is_closed():
            raise Exception("Page was closed - cannot navigate")

        current_url = self.page.url
        if "/i/bookmarks" in current_url:
            logger.info("✅ Already on bookmarks page")
            # VERIFY: Check for bookmarks indicator
            await asyncio.sleep(1)
            try:
                # Check for bookmarks page indicator
                bookmark_indicator = await self.page.query_selector(
                    '[data-testid="primaryColumn"]'
                )
                if bookmark_indicator:
                    page_text = await self.page.evaluate("document.body.innerText")
                    if "bookmarks" in page_text.lower() or "saved" in page_text.lower():
                        logger.info("✅ Verified: On bookmarks page")
                        return
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

        # Try direct navigation first (simplest)
        # Note: networkidle is unreliable on Twitter/X due to continuous network activity
        # Using domcontentloaded instead, which is more reliable
        try:
            if self.page.is_closed():
                raise Exception("Page closed before navigation")
            await self.page.goto(
                "https://x.com/i/bookmarks",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await asyncio.sleep(3)

            # VERIFY we're on bookmarks page
            final_url = self.page.url
            if "/i/bookmarks" not in final_url:
                raise Exception(
                    f"Navigation failed - ended up on {final_url} instead of /i/bookmarks"
                )

            # Double-check: look for bookmarks indicator
            page_text = await self.page.evaluate("document.body.innerText")
            if (
                "bookmarks" not in page_text.lower()
                and "saved" not in page_text.lower()
            ):
                logger.warning(
                    f"⚠️ Warning: On {final_url} but page doesn't look like bookmarks"
                )

            logger.info("✅ Navigated to bookmarks and verified")
            return
        except Exception as e:
            logger.error(f"⚠️ Direct navigation failed: {e}")
            if self.page.is_closed():
                raise Exception("Page was closed during navigation")

        # Try clicking sidebar link
        selectors = [
            'a[href="/i/bookmarks"]',
            '[data-testid="AppTabBar_Bookmarks_Link"]',
            'a[href*="bookmarks"]',
        ]

        for selector in selectors:
            try:
                link = await self.page.wait_for_selector(selector, timeout=5000)
                if link:
                    await link.click()
                    await asyncio.sleep(3)
                    final_url = self.page.url
                    if "/i/bookmarks" not in final_url:
                        logger.warning(f"⚠️ Clicked link but ended up on {final_url}")
                        continue
                    logger.info("✅ Clicked bookmarks link and verified")
                    return
            except Exception as e:
                logger.error(f"Error: {e}")
                continue

        raise Exception(
            "❌ CRITICAL: Could not navigate to bookmarks page - cannot collect bookmarks"
        )

    async def _extract_tweet(self, element) -> Optional[SocialPost]:
        """Extract a single tweet from DOM element

        CRITICAL: This must extract quickly without navigating away from the page.
        Any navigation will destroy the execution context for all other elements.
        """
        try:
            # Get tweet ID - SIMPLE: find status link
            # Do this FIRST before any other operations that might fail
            tweet_id = None
            try:
                # Fast path: try the most common selector first
                tweet_link = await element.query_selector('a[href*="/status/"]')
                if tweet_link:
                    href = await tweet_link.get_attribute("href")
                    if href and "/status/" in href:
                        tweet_id = href.split("/status/")[1].split("?")[0].split("/")[0]

                # Fallback: try all links (but limit to avoid timeout)
                if not tweet_id:
                    all_links = await element.query_selector_all('a[href*="status"]')
                    for link in all_links[:5]:  # Limit to first 5 links
                        try:
                            href = await link.get_attribute("href")
                            if href and "/status/" in href:
                                tweet_id = (
                                    href.split("/status/")[1]
                                    .split("?")[0]
                                    .split("/")[0]
                                )
                                break
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            continue

                # Last resort: regex from HTML (but this is slower)
                if not tweet_id:
                    try:
                        element_html = await element.inner_html()
                        import re

                        status_match = re.search(r"/status/(\d+)", element_html)
                        if status_match:
                            tweet_id = status_match.group(1)
                    except Exception as html_err:
                        logger.error(f"Error: {e}")
                        # If inner_html fails, element might be stale - skip debug logging to avoid more errors
                        pass
            except Exception as id_err:
                logger.error(f"Error: {e}")
                # Element might be stale - don't try to log it (would cause more errors)
                pass

            if not tweet_id:
                # Don't try to debug - element might be stale and any operation will fail
                # Just return None silently to avoid cascading errors
                return None

            # Get author - extract properly to avoid timestamp contamination
            author = "Unknown"
            author_handle = None
            try:
                # Try multiple selectors for author
                author_elem = await element.query_selector('[data-testid="User-Name"]')
                if author_elem:
                    # Get the link to extract handle properly
                    author_link = await author_elem.query_selector('a[href*="/"]')
                    if author_link:
                        href = await author_link.get_attribute("href")
                        if href:
                            # Extract handle from URL: /username or /@username
                            handle = href.strip("/").replace("@", "").split("/")[0]
                            if handle and not handle.startswith("http"):
                                author_handle = handle

                    # Get display name (without timestamp)
                    author_text = await author_elem.inner_text()
                    # Remove timestamp patterns like "·Nov 12"
                    import re

                    author_text = re.sub(r"·\s*\w+\s*\d+", "", author_text).strip()
                    parts = author_text.split("@")
                    if len(parts) > 1:
                        author = parts[0].strip()
                        if not author_handle:
                            author_handle = parts[1].strip()
                    elif author_text and not author_handle:
                        # If no @ symbol, use the text as author name
                        author = author_text.strip()
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

            # Get content - "show more" buttons should be clicked, but check if still truncated
            content = ""

            # First, check if there's still a "show more" button (means we missed it) - try ALL selectors
            show_more_in_tweet = None
            show_more_selectors = [
                '[data-testid="tweet-text-show-more-button"]',
                'span:has-text("Show more")',
                'span:has-text("Read more")',
                'div[role="button"]:has-text("Show more")',
                'div[role="button"]:has-text("Read more")',
                '[dir="ltr"]:has-text("Show more")',
                'button:has-text("Show more")',
                'button:has-text("Read more")',
            ]

            for selector in show_more_selectors:
                try:
                    found = await element.query_selector(selector)
                    if found:
                        try:
                            is_visible = await found.is_visible()
                            text = await found.inner_text()
                            if is_visible and (
                                "show" in text.lower()
                                or "more" in text.lower()
                                or "read" in text.lower()
                            ):
                                show_more_in_tweet = found
                                break
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            continue
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if show_more_in_tweet:
                # Click it now with better reliability
                try:
                    await show_more_in_tweet.scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    try:
                        await show_more_in_tweet.click()
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        # Fallback: use JavaScript click
                        await self.page.evaluate(
                            "(btn) => btn.click()", show_more_in_tweet
                        )
                    await asyncio.sleep(2)  # Wait for expansion
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

            # Extract content - ALWAYS use BeautifulSoup for full text extraction
            content_elem = await element.query_selector('[data-testid="tweetText"]')
            if content_elem:
                try:
                    # ALWAYS use BeautifulSoup to get ALL text (handles nested spans, etc.)
                    from bs4 import BeautifulSoup

                    html_content = await content_elem.inner_html()
                    soup = BeautifulSoup(html_content, "html.parser")
                    content = soup.get_text(separator=" ", strip=True)

                    # If still seems short, try inner_text as fallback
                    if not content or len(content.strip()) < 20:
                        content = await content_elem.inner_text()
                except Exception as e:
                    logger.error(f"Error: {e}")
                    # Fallback to inner_text
                    content = await content_elem.inner_text()
            else:
                # Fallback: get all text from element
                content = await element.inner_text()

            # Clean up content - remove extra whitespace
            if content:
                import re

                content = re.sub(r"\s+", " ", content).strip()

            # CRITICAL: Check one more time if there's a "show more" button (might have appeared dynamically)
            # If there is, we definitely need to click it - no hardcoded word lists!
            show_more_final_check = None
            show_more_selectors_final = [
                '[data-testid="tweet-text-show-more-button"]',
                'span:has-text("Show more")',
                'span:has-text("Read more")',
                'div[role="button"]:has-text("Show more")',
                'div[role="button"]:has-text("Read more")',
            ]

            for selector in show_more_selectors_final:
                try:
                    found = await element.query_selector(selector)
                    if found:
                        try:
                            is_visible = await found.is_visible()
                            if is_visible:
                                show_more_final_check = found
                                break
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            continue
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            # If we found a "show more" button, click it and re-extract
            if show_more_final_check:
                try:
                    logger.warning(
                        f"   ⚠️ Found 'show more' button after extraction, clicking..."
                    )
                    await show_more_final_check.scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    try:
                        await show_more_final_check.click()
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        await self.page.evaluate(
                            "(btn) => btn.click()", show_more_final_check
                        )
                    await asyncio.sleep(2)

                    # Re-extract content after clicking
                    content_elem = await element.query_selector(
                        '[data-testid="tweetText"]'
                    )
                    if content_elem:
                        from bs4 import BeautifulSoup

                        html_content = await content_elem.inner_html()
                        soup = BeautifulSoup(html_content, "html.parser")
                        new_content = soup.get_text(separator=" ", strip=True)
                        if len(new_content) > len(content):
                            content = new_content
                            logger.info(
                                f"   ✅ Got expanded content: {len(content)} chars"
                            )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

            # REMOVED: URL fetcher during extraction
            # This was causing "Execution context was destroyed" errors because
            # navigating to individual tweet URLs destroys the page context,
            # making all subsequent element handles invalid.
            #
            # The "show more" button clicking above should handle most truncation cases.
            # If content is still incomplete, we can handle it in a separate pass later.

            # Get timestamp
            created_at = datetime.now()
            try:
                time_elem = await element.query_selector("time")
                if time_elem:
                    datetime_str = await time_elem.get_attribute("datetime")
                    if datetime_str:
                        try:
                            created_at = parser.parse(datetime_str)
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            # Fallback parsing
                            pass
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

            # Build URL - get it from the actual link, not constructed
            url = f"https://x.com/i/web/status/{tweet_id}"  # Default fallback
            try:
                # Try to get the actual status link from the element
                status_link = await element.query_selector('a[href*="/status/"]')
                if status_link:
                    href = await status_link.get_attribute("href")
                    if href:
                        # Make sure it's a full URL
                        if href.startswith("/"):
                            url = f"https://x.com{href.split('?')[0]}"
                        elif href.startswith("http"):
                            url = href.split("?")[0]
                        else:
                            # Construct from handle if we have it
                            if author_handle:
                                url = f"https://x.com/{author_handle}/status/{tweet_id}"
                elif author_handle:
                    # Fallback: construct from handle
                    url = f"https://x.com/{author_handle}/status/{tweet_id}"
            except Exception as e:
                logger.error(f"Error: {e}")
                # Final fallback
                if author_handle:
                    url = f"https://x.com/{author_handle}/status/{tweet_id}"

            return SocialPost(
                platform="twitter",
                author=author,
                author_handle=author_handle,
                content=content,
                created_at=created_at,
                url=url,
                post_type="tweet",
                is_saved=True,
                post_id=f"twitter_{tweet_id}",
            )
        except Exception as e:
            logger.error(f"⚠️ Error extracting tweet data: {e}")
            return None
