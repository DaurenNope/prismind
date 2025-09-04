#!/usr/bin/env python3
"""
Test script for the Playwright Threads extractor.
Run with: python -m tests.test_threads_extractor
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip all Threads tests for now due to IP ban / disabled Threads collection
pytestmark = pytest.mark.skip(reason="Threads temporarily disabled (IP ban)")

# Add src to path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.extraction.social_extractor_base import SocialPost
from core.extraction.threads_extractor import ThreadsExtractor


@pytest.fixture
def threads_extractor():
    return ThreadsExtractor()

@pytest.fixture
def mock_playwright():
    with patch('core.extraction.threads_extractor.async_playwright') as mock:
        # Mock browser context
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_browser = MagicMock()
        
        # Setup chain
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock().chromium.launch.return_value = mock_browser
        
        # Mock page content to be a string by default
        mock_page.content.return_value = "<html></html>"
        
        # Mock successful page loads by default
        mock_page.wait_for_selector.return_value = True
        
        # Return both the main mock and the page mock for convenience
        yield mock, mock_page
        
        # Clean up - we don't need to verify close() since it's handled by context manager
        pass

def test_init(threads_extractor):
    """Test ThreadsExtractor initialization"""
    assert threads_extractor.platform_name == "threads"

def test_authenticate_success(threads_extractor, mock_playwright):
    """Test successful authentication"""
    mock, mock_page = mock_playwright
    
    # Mock successful login
    mock_page.wait_for_selector.return_value = True
    
    # Create a new mock chain for the test
    mock_context = MagicMock()
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_browser.close.return_value = None
    
    # Mock the sync_playwright context manager
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.__enter__.return_value = mock_pw
    mock_pw.__exit__.return_value = None
    
    with patch('core.extraction.threads_extractor.async_playwright', return_value=mock_pw):
        result = threads_extractor.authenticate("test_user", "test_pass")
        assert result is True
        
        # Verify login flow
        mock_page.goto.assert_called_with("https://www.threads.net/login")
        mock_page.fill.assert_any_call('input[name="username"]', "test_user")
        mock_page.fill.assert_any_call('input[name="password"]', "test_pass")
        mock_page.click.assert_called_with('button[type="submit"]')
        mock_page.wait_for_selector.assert_called_with('[data-pressable-container=true]', timeout=15000)

def test_authenticate_failure(threads_extractor, mock_playwright):
    """Test failed authentication"""
    mock, mock_page = mock_playwright
    
    # Mock failed login
    mock_page.wait_for_selector.side_effect = Exception("Timeout")
    
    # Create a new mock chain for the test
    mock_context = MagicMock()
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_browser.close.return_value = None
    
    # Mock the sync_playwright context manager
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.__enter__.return_value = mock_pw
    mock_pw.__exit__.return_value = None
    
    with patch('core.extraction.threads_extractor.async_playwright', return_value=mock_pw):
        result = threads_extractor.authenticate("test_user", "test_pass")
        assert result is False
        
        # Verify login attempt was made
        mock_page.goto.assert_called_with("https://www.threads.net/login")
        mock_page.fill.assert_any_call('input[name="username"]', "test_user")
        mock_page.fill.assert_any_call('input[name="password"]', "test_pass")

def test_parse_thread_data(threads_extractor):
    """Test parsing thread data from JSON"""
    test_data = {
        "post": {
            "caption": {"text": "Test post"},
            "taken_at": 1625097600,  # 2021-07-01 00:00:00 UTC
            "id": "123",
            "pk": "456",
            "code": "abc123",
            "user": {"username": "test_user"},
            "like_count": 42,
            "carousel_media": [
                {"image_versions2": {"candidates": [
                    {"url": "high_res.jpg"},
                    {"url": "low_res.jpg"}
                ]}}
            ],
            "video_versions": [{"url": "video.mp4"}]
        }
    }
    
    post = threads_extractor._parse_thread_data(test_data)
    
    assert isinstance(post, SocialPost)
    assert post.platform == "threads"
    assert post.post_id == "123"
    assert post.author == "test_user"
    assert post.content == "Test post"
    assert post.created_at == datetime.fromtimestamp(1625097600, tz=timezone.utc)
    assert post.url == "https://www.threads.net/@test_user/post/abc123"
    assert post.media_urls == ["video.mp4", "low_res.jpg"]
    assert post.engagement == {"likes": 42, "replies": 0}

def test_parse_thread_data_minimal(threads_extractor):
    """Test parsing thread data with minimal information"""
    test_data = {
        "post": {
            "id": "123",
            "pk": "456",
            "code": "abc123",
            "user": {"username": "test_user"},
            "taken_at": 1625097600,
            "caption": {"text": ""}
        }
    }
    
    post = threads_extractor._parse_thread_data(test_data)
    
    assert isinstance(post, SocialPost)
    assert post.content == ""
    assert not post.media_urls
    assert post.engagement == {"likes": 0, "replies": 0}

def test_parse_thread_data_invalid(threads_extractor):
    """Test parsing invalid thread data"""
    test_data = {"post": {}}  # Missing required fields
    post = threads_extractor._parse_thread_data(test_data)
    assert post is None

def test_scrape_thread_data_success(threads_extractor, mock_playwright):
    """Test successful scraping of thread data from URL"""
    mock, mock_page = mock_playwright
    
    # Mock page content with thread data
    mock_page.content.return_value = '''
        <html>
            <script type="application/json" data-sjs>
                {
                    "ScheduledServerJS": true,
                    "thread_items": [[{
                        "post": {
                            "caption": {"text": "Test post"},
                            "taken_at": 1625097600,
                            "id": "123",
                            "pk": "456",
                            "code": "abc123",
                            "user": {"username": "test_user"},
                            "like_count": 42
                        }
                    }]]
                }
            </script>
        </html>
    '''
    
    # Mock successful page load
    mock_page.wait_for_selector.return_value = True
    
    # Create a new mock chain for the test
    mock_context = MagicMock()
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_browser.close.return_value = None
    
    # Mock the sync_playwright context manager
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.__enter__.return_value = mock_pw
    mock_pw.__exit__.return_value = None
    
    with patch('core.extraction.threads_extractor.async_playwright', return_value=mock_pw):
        post = threads_extractor._scrape_thread_data("https://www.threads.net/@test_user/post/abc123", mock_page)
        
        assert isinstance(post, SocialPost)
        assert post.post_id == "123"
        assert post.author == "test_user"
        assert post.content == "Test post"
        
        # Verify page navigation
        mock_page.goto.assert_called_with("https://www.threads.net/@test_user/post/abc123")
        mock_page.wait_for_selector.assert_called_with("[data-pressable-container=true]")

def test_scrape_thread_data_no_data(threads_extractor, mock_playwright):
    """Test scraping when no thread data is found"""
    mock, mock_page = mock_playwright
    
    # Mock page content without thread data
    mock_page.content.return_value = '<html><body>No thread data here</body></html>'
    
    post = threads_extractor._scrape_thread_data("https://www.threads.net/@test_user/post/abc123", mock_page)
    assert post is None

def test_scrape_posts_from_urls(threads_extractor, mock_playwright):
    """Test scraping multiple posts from URLs"""
    mock, mock_page = mock_playwright
    
    # Mock page content for two different posts
    mock_page.content.side_effect = [
        '''
        <html>
            <script type="application/json" data-sjs>
                {
                    "ScheduledServerJS": true,
                    "thread_items": [[{
                        "post": {
                            "caption": {"text": "Post 1"},
                            "taken_at": 1625097600,
                            "id": "123",
                            "pk": "456",
                            "code": "abc123",
                            "user": {"username": "test_user"},
                            "like_count": 42
                        }
                    }]]
                }
            </script>
        </html>
        ''',
        '''
        <html>
            <script type="application/json" data-sjs>
                {
                    "ScheduledServerJS": true,
                    "thread_items": [[{
                        "post": {
                            "caption": {"text": "Post 2"},
                            "taken_at": 1625097600,
                            "id": "789",
                            "pk": "012",
                            "code": "def456",
                            "user": {"username": "test_user"},
                            "like_count": 21
                        }
                    }]]
                }
            </script>
        </html>
        '''
    ]
    
    # Mock successful page loads
    mock_page.wait_for_selector.return_value = True
    
    # Create a new mock chain for the test
    mock_context = MagicMock()
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_browser.close.return_value = None
    
    # Mock the sync_playwright context manager
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.__enter__.return_value = mock_pw
    mock_pw.__exit__.return_value = None
    
    with patch('core.extraction.threads_extractor.async_playwright', return_value=mock_pw):
        urls = [
            "https://www.threads.net/@test_user/post/abc123",
            "https://www.threads.net/@test_user/post/def456"
        ]
        
        posts = threads_extractor.scrape_posts_from_urls(urls)
        
        assert len(posts) == 2
        assert posts[0].content == "Post 1"
        assert posts[1].content == "Post 2"
        assert posts[0].post_id == "123"
        assert posts[1].post_id == "789"
        
        # Verify page navigation for both URLs
        mock_page.goto.assert_any_call(urls[0])
        mock_page.goto.assert_any_call(urls[1])
        assert mock_page.wait_for_selector.call_count >= 2

@pytest.mark.integration
def test_get_saved_posts_integration():
    """Integration test for getting saved posts (requires credentials)"""
    username = os.getenv('THREADS_USERNAME')
    password = os.getenv('THREADS_PASSWORD')
    
    if not username or not password:
        pytest.skip("THREADS_USERNAME or THREADS_PASSWORD not set")
    
    # Use a test-specific cookies file
    cookies_path = "test_threads_cookies.json"
    
    try:
        extractor = ThreadsExtractor()
        
        # First authenticate to create cookies
        assert extractor.authenticate(username, password, cookies_path), "Authentication failed"
        
        # Then get saved posts
        posts = extractor.get_saved_posts(username=username, password=password, limit=1, cookies_path=cookies_path)
        
        assert isinstance(posts, list)
        if posts:
            post = posts[0]
            assert isinstance(post, SocialPost)
            assert post.platform == "threads"
            assert post.author
            assert post.url.startswith("https://www.threads.net/")
    finally:
        # Clean up cookies file
        try:
            if os.path.exists(cookies_path):
                os.remove(cookies_path)
        except Exception as e:
            logging.warning(f"Failed to clean up cookies file: {e}")

@pytest.mark.integration
def test_scrape_posts_from_urls_integration():
    """Integration test for scraping posts from URLs (no auth required)"""
    extractor = ThreadsExtractor()
    test_url = "https://www.threads.net/t/CuqgkHcL5dl/"  # Use a public, static thread URL
    
    posts = extractor.scrape_posts_from_urls([test_url])
    
    assert isinstance(posts, list)
    if posts:
        post = posts[0]
        assert isinstance(post, SocialPost)
        assert post.platform == "threads"
        assert post.author
        assert post.url.startswith("https://www.threads.net/")
        assert "CuqgkHcL5dl" in post.url 