#!/usr/bin/env python3
"""
Scrape Qronoya's Threads posts to use as voice examples
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from src.core.extraction.threads_extractor import ThreadsExtractor

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def scrape_qronoya_profile_posts(username: str = "qronoya", limit: int = 20):
    """
    Scrape posts from Qronoya's Threads profile.

    Args:
        username: Threads username (default: qronoya)
        limit: Number of posts to scrape (default: 20)

    Returns:
        List of post dictionaries with content
    """
    extractor = ThreadsExtractor()

    # Authenticate with cookies
    cookies_path = "config/threads_cookies.json"
    logging.info(f"Authenticating with cookies from {cookies_path}...")

    auth_success = await extractor.authenticate(
        username="qronoya",  # Your username for authentication
        password="",  # Not needed if cookies work
        cookies_path=cookies_path,
    )

    if not auth_success:
        logging.error("Failed to authenticate with Threads")
        return []

    logging.info(f"✅ Authenticated! Now scraping profile posts for @{username}...")

    # Navigate to user's profile
    profile_url = f"https://www.threads.net/@{username}"
    logging.info(f"Navigating to {profile_url}...")

    await extractor.page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    # Scroll to load posts
    posts_scraped = []
    scroll_count = 0
    max_scrolls = 5  # Adjust based on how many posts you want

    while scroll_count < max_scrolls and len(posts_scraped) < limit:
        logging.info(f"Scroll {scroll_count + 1}/{max_scrolls}...")

        # Get all post links on current page
        post_links = await extractor.page.evaluate(
            """
            () => {
                const links = Array.from(document.querySelectorAll('a[href*="/post/"]'));
                return links.map(link => link.href).filter(url => url.includes('/post/'));
            }
        """
        )

        # Remove duplicates
        unique_links = list(set(post_links))
        logging.info(f"Found {len(unique_links)} unique post links on page")

        # Scrape each post's content
        for link in unique_links[:limit]:
            if len(posts_scraped) >= limit:
                break

            # Check if already scraped
            if any(p.get("url") == link for p in posts_scraped):
                continue

            logging.info(f"Scraping post: {link}")

            try:
                # Use extractor's scraping method
                post = await extractor._scrape_thread_data_async(link, extractor.page)

                if post and post.content:
                    posts_scraped.append(
                        {
                            "url": link,
                            "content": post.content,
                            "author": post.author,
                            "created_at": post.created_at.isoformat()
                            if post.created_at
                            else None,
                            "platform": "threads",
                        }
                    )
                    logging.info(
                        f"✅ Scraped post #{len(posts_scraped)}: {post.content[:100]}..."
                    )
                else:
                    logging.warning(f"Failed to scrape content from {link}")

            except Exception as e:
                logging.error(f"Error scraping {link}: {e}")
                continue

        # Scroll down
        await extractor.page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(2)
        scroll_count += 1

    # Close browser
    await extractor.browser.close()
    await extractor.pw.stop()

    logging.info(f"\n✅ Scraped {len(posts_scraped)} posts from @{username}")
    return posts_scraped


async def update_qronoya_examples(posts: list):
    """
    Update qronoya_examples.json with scraped posts

    Args:
        posts: List of post dictionaries from scraping
    """
    examples_file = Path("config/personas/qronoya_examples.json")

    # Load existing structure
    with open(examples_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Update examples with real posts
    for i, post in enumerate(posts[:15]):  # Take first 15
        if i < len(data["examples"]):
            data["examples"][i]["platform"] = "threads"
            data["examples"][i]["content"] = post["content"]
            data["examples"][i][
                "notes"
            ] = f"Real post from @qronoya - {post.get('created_at', 'unknown date')}"
            data["examples"][i][
                "why_good_example"
            ] = "Authentic voice from actual Threads post"

    # Save updated file
    with open(examples_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logging.info(f"✅ Updated {examples_file} with {min(15, len(posts))} real posts")


async def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("SCRAPING QRONOYA'S THREADS POSTS FOR VOICE EXAMPLES")
    print("=" * 80 + "\n")

    # Scrape posts
    posts = await scrape_qronoya_profile_posts(username="qronoya", limit=20)

    if not posts:
        print("❌ No posts scraped. Check authentication and profile visibility.")
        return

    # Show preview
    print("\n" + "=" * 80)
    print("SCRAPED POSTS PREVIEW")
    print("=" * 80 + "\n")

    for i, post in enumerate(posts[:5], 1):
        print(f"{i}. {post['content'][:150]}...")
        print(f"   URL: {post['url']}")
        print()

    # Auto-update (no interactive prompt needed)
    print(f"\nScraped {len(posts)} posts total.")
    print("Updating qronoya_examples.json with these posts...")

    await update_qronoya_examples(posts)

    print("\n" + "=" * 80)
    print("✅ SUCCESS! qronoya_examples.json updated with real voice examples!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review config/personas/qronoya_examples.json")
    print("2. Run: python demo_rewrites_comparison.py")
    print("3. Your Qronoya rewrites will now use authentic Russian voice!")
    print()

    # Also save to backup file
    backup_file = Path("scraped_qronoya_posts_backup.json")
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"✅ Backup saved to {backup_file}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
