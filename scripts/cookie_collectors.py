#!/usr/bin/env python3
"""
Cookie-based collectors for Reddit saved posts and Twitter bookmarks.

Reads cookies JSON from ./cookies/reddit.json and ./cookies/twitter.json,
opens the respective pages with Playwright, extracts items, and stores them
via DatabaseManager.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright

# Ensure local imports work when executed directly
import sys as _sys
from pathlib import Path as _Path
_sys.path.append(str(_Path(__file__).resolve().parents[1]))
from scripts.database_manager import DatabaseManager


COOKIES_DIR = Path("cookies")
REDDIT_COOKIES_PATH = COOKIES_DIR / "reddit.json"
TWITTER_COOKIES_PATH = COOKIES_DIR / "twitter.json"


def _normalize_same_site(value: Any) -> str:
    v = str(value or "").lower()
    if v in ("strict",):
        return "Strict"
    if v in ("lax",):
        return "Lax"
    if v in ("none", "no_restriction"):
        return "None"
    # 'unspecified' or anything else → pick Lax as safest default
    return "Lax"


def _load_cookies(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    norm: List[Dict[str, Any]] = []
    for c in raw:
        c2 = dict(c)
        # Playwright expects sameSite in (Strict|Lax|None)
        c2["sameSite"] = _normalize_same_site(c.get("sameSite"))
        # Ensure secure is boolean
        if "secure" in c2 and not isinstance(c2["secure"], bool):
            c2["secure"] = str(c2["secure"]).lower() == "true"
        # Ensure httpOnly is boolean
        if "httpOnly" in c2 and not isinstance(c2["httpOnly"], bool):
            c2["httpOnly"] = str(c2["httpOnly"]).lower() == "true"
        # Remove fields Playwright doesn't need
        for k in ("storeId",):
            c2.pop(k, None)
        norm.append(c2)
    return norm


def _store_posts(db: DatabaseManager, posts: List[Dict[str, Any]]) -> int:
    stored = 0
    for post in posts:
        try:
            db.add_post(post)
            stored += 1
        except Exception:
            # Likely duplicate post_id/URL; skip
            continue
    return stored


from typing import Optional


def collect_reddit_saved(db: DatabaseManager, username: Optional[str]) -> int:
    if not REDDIT_COOKIES_PATH.exists():
        print("❌ Reddit cookies not found at ./cookies/reddit.json")
        return 0

    cookies = _load_cookies(REDDIT_COOKIES_PATH)
    # Old Reddit uses simpler markup and is often easier to scrape when logged in via cookies
    url = (
        f"https://old.reddit.com/user/{username}/saved" if username else "https://old.reddit.com/user/me/saved"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        context.add_cookies(cookies)
        page = context.new_page()
        print(f"🔍 Opening {url}")
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Attempt lazy-load by scrolling
        for _ in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(800)

        # Try multiple selectors for modern/old layouts
        items = []
        selectors = [
            "div.thing",
            "div[data-testid='post-container']",
            "div.Post",
            "div[data-click-id='body']",
        ]
        for sel in selectors:
            elements = page.query_selector_all(sel)
            if elements:
                items = elements
                break

        print(f"✅ Found {len(items)} potential saved items")

        posts: List[Dict[str, Any]] = []
        now_iso = datetime.utcnow().isoformat()
        for el in items:
            try:
                title_el = (
                    el.query_selector("h3")
                    or el.query_selector("a[data-click-id='body']")
                    or el.query_selector("a.title")
                )
                title = title_el.inner_text().strip() if title_el else None
                if not title:
                    continue

                link_el = (
                    el.query_selector("a[data-click-id='body']")
                    or el.query_selector("a[href*='/comments/']")
                    or el.query_selector("a.title")
                )
                href = link_el.get_attribute("href") if link_el else None
                if href and not href.startswith("http"):
                    href = f"https://reddit.com{href}"

                sub_el = el.query_selector("a[data-click-id='subreddit']") or el.query_selector("a.subreddit")
                subreddit = sub_el.inner_text().strip() if sub_el else "r/unknown"

                author_el = el.query_selector("a[data-click-id='user']") or el.query_selector("a[href*='/user/']")
                author = author_el.inner_text().strip() if author_el else "Unknown"

                post_id = href.split("/comments/")[-1].split("/")[0] if href and "/comments/" in href else href or title[:32]

                posts.append({
                    'platform': 'reddit',
                    'post_id': post_id,
                    'author': author,
                    'author_handle': author if author.startswith('u/') else f"u/{author}",
                    'content': title,
                    'created_at': now_iso,
                    'url': href,
                    'post_type': 'post',
                    'media_urls': [],
                    'hashtags': [],
                    'mentions': [],
                    'engagement_score': None,
                    'value_score': None,
                    'sentiment': None,
                    'folder_category': subreddit,
                    'ai_summary': None,
                    'key_concepts': [],
                    'is_saved': 1,
                    'saved_at': now_iso,
                })
            except Exception:
                continue

        browser.close()

    stored = _store_posts(db, posts)
    print(f"✅ Reddit saved: stored {stored} posts")
    return stored


def collect_twitter_bookmarks(db: DatabaseManager) -> int:
    if not TWITTER_COOKIES_PATH.exists():
        print("❌ Twitter cookies not found at ./cookies/twitter.json")
        return 0

    cookies = _load_cookies(TWITTER_COOKIES_PATH)
    url = "https://x.com/i/bookmarks"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        print(f"🔍 Opening {url}")
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Scroll to load items
        for _ in range(4):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(800)

        tweet_items = page.query_selector_all("article div[data-testid='tweetText']")
        print(f"✅ Found {len(tweet_items)} potential bookmarked tweets")

        posts: List[Dict[str, Any]] = []
        now_iso = datetime.utcnow().isoformat()
        for container in tweet_items:
            try:
                text = container.inner_text().strip()
                # Find tweet root article to access header/author/link
                art = container.closest("article")
                if not art:
                    continue
                author_el = art.query_selector("div[dir='ltr'] span")
                author = author_el.inner_text().strip() if author_el else "Unknown"
                link_el = art.query_selector("a[href*='/status/']")
                href = link_el.get_attribute("href") if link_el else None
                if href and not href.startswith("http"):
                    href = f"https://x.com{href}"
                post_id = href.split("/status/")[-1].split("?")[0] if href and "/status/" in href else (href or text[:32])

                posts.append({
                    'platform': 'twitter',
                    'post_id': post_id,
                    'author': author,
                    'author_handle': author,
                    'content': text,
                    'created_at': now_iso,
                    'url': href,
                    'post_type': 'post',
                    'media_urls': [],
                    'hashtags': [],
                    'mentions': [],
                    'engagement_score': None,
                    'value_score': None,
                    'sentiment': None,
                    'folder_category': 'bookmarks',
                    'ai_summary': None,
                    'key_concepts': [],
                    'is_saved': 1,
                    'saved_at': now_iso,
                })
            except Exception:
                continue

        browser.close()

    stored = _store_posts(db, posts)
    print(f"✅ Twitter bookmarks: stored {stored} posts")
    return stored


def main():
    db = DatabaseManager()
    username = os.getenv('REDDIT_USERNAME', '').strip()

    total = 0
    # Always attempt; function will use /user/me/saved if username missing
    total += collect_reddit_saved(db, username or None)

    total += collect_twitter_bookmarks(db)
    print(f"🎉 Cookie-based collection complete. Stored: {total}")


if __name__ == "__main__":
    main()


