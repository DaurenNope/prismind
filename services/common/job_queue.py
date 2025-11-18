"""
Shared Redis queue helpers for job orchestration.
"""

import os
from functools import lru_cache
from typing import Sequence

from redis import Redis
from rq import Queue

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


@lru_cache(maxsize=1)
def get_redis_connection() -> Redis:
    """Return a cached Redis connection using REDIS_URL."""
    redis_url = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
    return Redis.from_url(redis_url)


def get_queue(name: str) -> Queue:
    """Get (or lazily create) an RQ queue by name."""
    return Queue(name=name, connection=get_redis_connection())


def get_queues(names: Sequence[str]) -> Sequence[Queue]:
    """Helper to fetch multiple queues at once."""
    conn = get_redis_connection()
    return [Queue(name=name, connection=conn) for name in names]
