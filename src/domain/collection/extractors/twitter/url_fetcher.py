import logging

logger = logging.getLogger(__name__)
"""Extract full content from a single Twitter post URL - reusable module"""

import asyncio
from typing import Optional

from playwright.async_api import Page


async def fetch_tweet_content_from_url(page: Page, post_url: str) -> Optional[str]:
    """
    Fetch full content from a Twitter post URL.

    This is a reusable function that can be used by:
    - The bookmarks collector
    - The URL fix script
    - Any other component that needs to fetch tweet content

    Args:
        page: Authenticated Playwright page
        post_url: The Twitter post URL (e.g., https://x.com/user/status/123456)

    Returns:
        Full content string, or None if failed
    """
    try:
        # Normalize URL - ensure it's the correct format
        if "x.com" not in post_url and "twitter.com" not in post_url:
            return None

        # Navigate to the post URL - wait for network to be idle
        await page.goto(post_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)  # Wait longer for page to fully load

        # Check current URL - make sure we're on the tweet page, not explore/home
        current_url = page.url

        if "/status/" not in current_url:
            # Twitter might have redirected - try navigating again with explicit wait
            await asyncio.sleep(2)
            await page.goto(post_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            current_url = page.url

            # If still not on tweet page, it's likely an auth issue or the tweet doesn't exist
            if "/status/" not in current_url:
                # Check if we're on explore/home - this means auth failed or tweet is gone
                if "/explore" in current_url or "/home" in current_url:
                    return None
                # Otherwise, maybe the URL format is different - continue anyway

        # Check for error pages
        page_text = await page.evaluate("document.body.innerText")
        if "something went wrong" in page_text.lower():
            await asyncio.sleep(2)
            await page.reload(wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

        # Wait for tweet to load
        try:
            await page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
        except Exception as e:
            logger.error(f"Error: {e}")
            pass  # Continue anyway

        # Find and click "Show more" button - SIMPLE and RELIABLE
        read_more_clicked = False

        # Try the official test ID first (most reliable)
        try:
            read_more_btn = await page.query_selector(
                '[data-testid="tweet-text-show-more-button"]'
            )
            if read_more_btn:
                is_visible = await read_more_btn.is_visible()
                if is_visible:
                    await read_more_btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    try:
                        await read_more_btn.click()
                        read_more_clicked = True
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        # Try JS click
                        await page.evaluate("(btn) => btn.click()", read_more_btn)
                        read_more_clicked = True
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # If official selector didn't work, try text-based selectors
        if not read_more_clicked:
            text_selectors = [
                'span:has-text("Show more")',
                'span:has-text("Read more")',
                'button:has-text("Show more")',
            ]
            for selector in text_selectors:
                try:
                    read_more_btn = await page.query_selector(selector)
                    if read_more_btn:
                        is_visible = await read_more_btn.is_visible()
                        if is_visible:
                            btn_text = await read_more_btn.inner_text()
                            if "show" in btn_text.lower() or "more" in btn_text.lower():
                                await read_more_btn.scroll_into_view_if_needed()
                                await asyncio.sleep(0.5)
                                try:
                                    await read_more_btn.click()
                                    read_more_clicked = True
                                    break
                                except Exception as e:
                                    logger.error(f"Error: {e}")
                                    try:
                                        await page.evaluate(
                                            "(btn) => btn.click()", read_more_btn
                                        )
                                        read_more_clicked = True
                                        break
                                    except Exception as e:
                                        logger.error(f"Error: {e}")
                                        continue
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

        # Wait for content to expand after clicking
        if read_more_clicked:
            await asyncio.sleep(3)  # Wait for expansion to complete
        else:
            await asyncio.sleep(1)  # Small wait even if no button found

        # Re-query the content element AFTER expansion to get full content
        # Extract content - try multiple strategies
        # Strategy 1: Primary selector - get ALL text from HTML
        # IMPORTANT: Find the CORRECT tweet by matching status ID from URL
        try:
            # Extract status ID from URL to find the correct tweet
            status_id = post_url.split("/status/")[-1].split("?")[0].split("/")[0]

            # Find ALL tweet articles
            all_tweets = await page.query_selector_all('article[data-testid="tweet"]')

            # Try to find the tweet that matches our status ID
            tweet_article = None
            for article in all_tweets:
                try:
                    # Check if this article contains a link to our status ID
                    links = await article.query_selector_all(
                        f'a[href*="/status/{status_id}"]'
                    )
                    if links:
                        tweet_article = article
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            # Fallback: if we can't find by status ID, use first article
            if not tweet_article and all_tweets:
                tweet_article = all_tweets[0]

            if not tweet_article:
                # Last fallback: try to find any tweet
                tweet_article = await page.query_selector('[data-testid="tweet"]')

            if tweet_article:
                # Get content from WITHIN the main tweet article
                content_elem = await tweet_article.query_selector(
                    '[data-testid="tweetText"]'
                )
                if content_elem:
                    # Get HTML and parse with BeautifulSoup to extract ALL text
                    html_content = await content_elem.inner_html()
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(html_content, "html.parser")
                    # Get all text, preserving structure
                    content = soup.get_text(separator=" ", strip=True)

                    # If content seems incomplete, try inner_text as fallback
                    if not content or len(content.strip()) < 20:
                        content = await content_elem.inner_text()

                    # Validate content - filter ads, not by length (short tweets are valid!)
                    if content and len(content.strip()) > 0:
                        # Filter obvious ads (all caps with spam patterns)
                        content_upper = content.upper()
                        is_ad = (
                            content.isupper()
                            and len(content) < 100
                            and (
                                "FIND THIS" in content_upper
                                or "CLICK HERE" in content_upper
                                or "GET RICH" in content_upper
                                or "MAKE MONEY" in content_upper
                            )
                        )
                        if not is_ad:
                            return content
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Strategy 2: Alternative selectors with HTML parsing (scoped to correct tweet)
        try:
            # Use same logic to find correct tweet
            status_id = post_url.split("/status/")[-1].split("?")[0].split("/")[0]
            all_tweets = await page.query_selector_all('article[data-testid="tweet"]')

            tweet_article = None
            for article in all_tweets:
                try:
                    links = await article.query_selector_all(
                        f'a[href*="/status/{status_id}"]'
                    )
                    if links:
                        tweet_article = article
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if not tweet_article and all_tweets:
                tweet_article = all_tweets[0]

            if not tweet_article:
                tweet_article = await page.query_selector(
                    'article[data-testid="tweet"]'
                )

            if tweet_article:
                for selector in ["[lang]", '[dir="auto"]']:
                    try:
                        content_elem = await tweet_article.query_selector(selector)
                        if content_elem:
                            # Get HTML first for better parsing
                            html_content = await content_elem.inner_html()
                            from bs4 import BeautifulSoup

                            soup = BeautifulSoup(html_content, "html.parser")
                            content = soup.get_text(separator=" ", strip=True)

                            # If too short, try inner_text
                            if not content or len(content.strip()) < 20:
                                content = await content_elem.inner_text()

                            # Filter ads, not by length
                            if content and len(content.strip()) > 0:
                                content_upper = content.upper()
                                is_ad = (
                                    content.isupper()
                                    and len(content) < 100
                                    and (
                                        "FIND THIS" in content_upper
                                        or "CLICK HERE" in content_upper
                                        or "GET RICH" in content_upper
                                        or "MAKE MONEY" in content_upper
                                    )
                                )
                                if not is_ad:
                                    return content
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Strategy 3: Fallback - extract from article (more aggressive)
        try:
            # Use same logic to find correct tweet
            status_id = post_url.split("/status/")[-1].split("?")[0].split("/")[0]
            all_tweets = await page.query_selector_all('article[data-testid="tweet"]')

            tweet_article = None
            for article in all_tweets:
                try:
                    links = await article.query_selector_all(
                        f'a[href*="/status/{status_id}"]'
                    )
                    if links:
                        tweet_article = article
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if not tweet_article and all_tweets:
                tweet_article = all_tweets[0]

            if not tweet_article:
                tweet_article = await page.query_selector(
                    'article[data-testid="tweet"]'
                )

            if tweet_article:
                # Get HTML and parse it properly
                html_content = await tweet_article.inner_html()
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html_content, "html.parser")

                # Find the main tweet text container
                tweet_text_elem = soup.find("div", {"data-testid": "tweetText"})
                if tweet_text_elem:
                    content = tweet_text_elem.get_text(separator=" ", strip=True)
                    # Filter ads, not by length
                    if content and len(content.strip()) > 0:
                        content_upper = content.upper()
                        is_ad = (
                            content.isupper()
                            and len(content) < 100
                            and (
                                "FIND THIS" in content_upper
                                or "CLICK HERE" in content_upper
                                or "GET RICH" in content_upper
                                or "MAKE MONEY" in content_upper
                            )
                        )
                        if not is_ad:
                            return content

                # Fallback: get all text from article and clean
                full_text = soup.get_text(separator="\n", strip=True)
                lines = full_text.split("\n")
                content_lines = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # Skip metadata
                    if line.startswith("@") and len(line) < 30:
                        continue
                    if "·" in line and len(line) < 20:
                        continue
                    if line.lower() in [
                        "show more",
                        "read more",
                        "show thread",
                        "replying to",
                    ]:
                        continue
                    # Skip engagement numbers (likes, retweets, etc.)
                    if (
                        line.replace(",", "").replace(".", "").isdigit()
                        and len(line) < 10
                    ):
                        continue
                    content_lines.append(line)
                content = "\n".join(content_lines)
                # Filter ads, not by length
                if content and len(content.strip()) > 0:
                    content_upper = content.upper()
                    is_ad = (
                        content.isupper()
                        and len(content) < 100
                        and (
                            "FIND THIS" in content_upper
                            or "CLICK HERE" in content_upper
                            or "GET RICH" in content_upper
                            or "MAKE MONEY" in content_upper
                        )
                    )
                    if not is_ad:
                        return content
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        return None

    except Exception as e:
        logger.error(f"Error: {e}")
        return None
