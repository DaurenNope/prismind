"""Shared utilities for Twitter extraction"""

import asyncio
import random
from typing import List


async def jitter(extra_ms: int = 0, jitter_ms: List[int] = None) -> None:
    """Sleep a random jitter to mimic human behavior."""
    if jitter_ms is None:
        jitter_ms = [300, 1200]

    try:
        low, high = (
            (jitter_ms[0], jitter_ms[1])
            if isinstance(jitter_ms, list) and len(jitter_ms) == 2
            else (300, 1200)
        )
        delay = max(0, low) if low == high else random.randint(int(low), int(high))
        await asyncio.sleep((delay + max(0, extra_ms)) / 1000)
    except Exception as e:
        logger.error(f"Error: {e}")
        await asyncio.sleep(0.3)
