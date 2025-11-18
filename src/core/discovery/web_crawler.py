#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Web Crawler for BEYONDLINES using Crawl4AI
Extracts clean content from any webpage
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.extraction.social_extractor_base import SocialPost


class WebCrawler:
    """Universal web crawler for content extraction"""

    def __init__(self):
        self.crawler = None

    async def _init_crawler(self):
        """Initialize Crawl4AI crawler"""
        if self.crawler is None:
            try:
                from crawl4ai import AsyncWebCrawler

                self.crawler = AsyncWebCrawler()
                await self.crawler.__aenter__()
            except Exception as e:
                logger.warning(f"⚠️ Crawl4AI not available: {e}")
                self.crawler = None

    async def crawl_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl a single URL and extract clean content

        Returns:
            Dict with title, content, markdown, metadata
        """
        await self._init_crawler()

        if not self.crawler:
            return None

        try:
            result = await self.crawler.arun(url=url)

            if result.success:
                return {
                    "url": url,
                    "title": result.metadata.get("title", ""),
                    "description": result.metadata.get("description", ""),
                    "content": result.cleaned_html or result.markdown,
                    "markdown": result.markdown,
                    "metadata": result.metadata,
                    "extracted_at": datetime.now(),
                }
            else:
                logger.error(f"   ❌ Failed to crawl {url}: {result.error_message}")
                return None

        except Exception as e:
            logger.error(f"   ❌ Error crawling {url}: {e}")
            return None

    async def crawl_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Crawl multiple URLs in parallel

        Args:
            urls: List of URLs to crawl

        Returns:
            List of successfully crawled content
        """
        logger.info(f"🌐 Crawling {len(urls)} URLs...")

        tasks = [self.crawl_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        successful = [r for r in results if isinstance(r, dict) and r is not None]

        logger.info(f"   ✅ Successfully crawled {len(successful)}/{len(urls)} URLs")
        return successful

    async def discover_from_search(
        self, query: str, num_results: int = 10
    ) -> List[SocialPost]:
        """
        Search web and crawl top results

        Note: Requires search API or DuckDuckGo
        """
        logger.debug(f"🔍 Searching web for: {query}")

        try:
            # Use DuckDuckGo search (no API key needed)
            from duckduckgo_search import DDGS

            ddgs = DDGS()
            search_results = list(ddgs.text(query, max_results=num_results))

            # Extract URLs
            urls = [
                result.get("href") for result in search_results if result.get("href")
            ]

            logger.info(f"   Found {len(urls)} URLs to crawl")

            # Crawl all URLs
            crawled = await self.crawl_urls(urls[:num_results])

            # Convert to SocialPost
            posts = []
            for item in crawled:
                post = SocialPost(
                    post_id=f"web_{hash(item['url'])}",
                    platform="web",
                    author=item.get("metadata", {}).get("author", "Web"),
                    author_handle=item["url"].split("/")[2]
                    if "/" in item["url"]
                    else "web",
                    content=f"{item['title']}\n\n{item['description']}\n\n{item['content'][:500]}",
                    url=item["url"],
                    created_at=datetime.now(),
                    post_type="article",
                )
                posts.append(post)

            logger.info(f"   ✅ Created {len(posts)} posts from web content")
            return posts

        except Exception as e:
            logger.error(f"   ❌ Web search error: {e}")
            return []

    async def crawl_specific_sites(self, keywords: List[str]) -> List[SocialPost]:
        """
        Crawl specific high-value sites for keywords

        Sites: Product Hunt, Dev.to, Medium, Substack, etc.
        """
        logger.info(f"🎯 Crawling high-value sites for keywords...")

        posts = []

        # Product Hunt - trending products
        try:
            ph_url = "https://www.producthunt.com/"
            ph_content = await self.crawl_url(ph_url)

            if ph_content:
                # Check if content matches keywords
                content_lower = ph_content["content"].lower()
                if any(kw.lower() in content_lower for kw in keywords[:20]):
                    post = SocialPost(
                        post_id=f"producthunt_{datetime.now().timestamp()}",
                        platform="web",
                        author="Product Hunt",
                        author_handle="producthunt",
                        content=f"Product Hunt Trending\n\n{ph_content['content'][:500]}",
                        url=ph_url,
                        created_at=datetime.now(),
                        post_type="article",
                    )
                    posts.append(post)
                    logger.info(f"   ✅ Product Hunt content matched keywords")
        except Exception as e:
            logger.error(f"   ⚠️ Product Hunt crawl failed: {e}")

        # Dev.to - latest posts
        try:
            devto_url = "https://dev.to/top/week"
            devto_content = await self.crawl_url(devto_url)

            if devto_content:
                content_lower = devto_content["content"].lower()
                if any(kw.lower() in content_lower for kw in keywords[:20]):
                    post = SocialPost(
                        post_id=f"devto_{datetime.now().timestamp()}",
                        platform="web",
                        author="Dev.to",
                        author_handle="devto",
                        content=f"Dev.to Top This Week\n\n{devto_content['content'][:500]}",
                        url=devto_url,
                        created_at=datetime.now(),
                        post_type="article",
                    )
                    posts.append(post)
                    logger.info(f"   ✅ Dev.to content matched keywords")
        except Exception as e:
            logger.error(f"   ⚠️ Dev.to crawl failed: {e}")

        logger.info(f"   Total from specific sites: {len(posts)}")
        return posts

    async def close(self):
        """Close the crawler"""
        if self.crawler:
            try:
                await self.crawler.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass


# Trending content sources to crawl
TRENDING_SOURCES = [
    "https://news.ycombinator.com/",
    "https://www.producthunt.com/",
    "https://dev.to/top/week",
    "https://github.com/trending",
]
