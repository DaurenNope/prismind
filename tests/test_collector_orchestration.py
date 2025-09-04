import asyncio

import pandas as pd

from services.collector_runner import (
    collect_reddit_bookmarks,
    collect_twitter_bookmarks,
)


class FakeDB:
    def __init__(self):
        self._rows = []

    def get_all_posts(self, include_deleted=False):
        if not self._rows:
            return pd.DataFrame()
        return pd.DataFrame(self._rows)

    def add_post(self, post):
        self._rows.append(post)


def test_collect_twitter_with_mocked_extractor(monkeypatch):
    # Monkeypatch Twitter extractor to return a deterministic set
    async def fake_get_saved_posts(self, limit=200):  # noqa: ARG002
        return [
            {"platform": "twitter", "post_id": "tw1", "content": "A", "url": "u1"},
            {"platform": "twitter", "post_id": "tw2", "content": "B", "url": "u2"},
        ]

    class FakeExtractor:
        def __init__(self, *args, **kwargs):  # noqa: D401, ANN001, ANN002
            pass

        async def get_saved_posts(self, limit=200):  # noqa: D401, ARG002
            return await fake_get_saved_posts(self, limit=limit)

        async def close(self):  # noqa: D401
            return None

    monkeypatch.setattr(
        "services.collector_runner.TwitterExtractorPlaywright", FakeExtractor, raising=True
    )

    db = FakeDB()
    existing_ids = set()
    existing_urls = set()
    out = asyncio.run(collect_twitter_bookmarks(db, existing_ids, existing_urls))
    assert out == 2


def test_collect_reddit_with_mocked_extractor(monkeypatch):
    # Set environment variable to allow tests without credentials
    monkeypatch.setenv('ALLOW_REDDIT_TESTS_WITHOUT_CREDS', '1')
    
    class FakeReddit:
        def __init__(self, *args, **kwargs):  # noqa: D401, ANN001, ANN002
            pass

        def get_saved_posts(self, limit=100):  # noqa: D401, ARG002
            return [
                {"platform": "reddit", "post_id": "rd1", "content": "A", "url": "u1"},
                {"platform": "reddit", "post_id": "rd2", "content": "B", "url": "u2"},
            ]

    monkeypatch.setattr(
        "services.collector_runner.RedditExtractor", FakeReddit, raising=True
    )

    db = FakeDB()
    existing_ids = set()
    existing_urls = set()
    out = collect_reddit_bookmarks(db, existing_ids, existing_urls)
    assert out == 2


