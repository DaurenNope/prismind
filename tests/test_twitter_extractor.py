import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright

# Load environment variables
load_dotenv()

@pytest.fixture(scope="module")
async def extractor():
    username = os.getenv('TWITTER_USERNAME')
    password = os.getenv('TWITTER_PASSWORD')
    
    if not username:
        pytest.skip("TWITTER_USERNAME not found in .env file")

    headless_mode = os.getenv('HEADLESS', 'true').lower() == 'true'
    
    extractor = TwitterExtractorPlaywright(
        username=username,
        password=password,
        headless=headless_mode
    )
    
    authenticated = await extractor.authenticate()
    if not authenticated:
        pytest.fail("Twitter authentication failed")
        
    yield extractor
    
    await extractor.close()

@pytest.mark.asyncio
async def test_authentication(extractor: TwitterExtractorPlaywright):
    assert extractor.is_authenticated is True

@pytest.mark.asyncio
async def test_get_saved_posts(extractor: TwitterExtractorPlaywright):
    saved_posts = await extractor.get_saved_posts(limit=5)
    assert isinstance(saved_posts, list)
    if saved_posts:
        post = saved_posts[0]
        assert post.author is not None
        assert post.content is not None
        assert post.url is not None

@pytest.mark.asyncio
async def test_get_liked_posts(extractor: TwitterExtractorPlaywright):
    liked_posts = await extractor.get_liked_posts(limit=3)
    assert isinstance(liked_posts, list)
    if liked_posts:
        post = liked_posts[0]
        assert post.author is not None
        assert post.content is not None
        assert post.url is not None