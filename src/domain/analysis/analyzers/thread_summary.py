#!/usr/bin/env python3
"""
Thread Summary Data Structure
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ThreadSummary:
    """Thread summary data structure"""
    main_topic: str
    key_points: List[str]
    insights: List[str]
    sentiment: str
    action_items: List[str]
    summary: str
    confidence: float
    ai_service_used: str
