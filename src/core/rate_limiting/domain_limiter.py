"""
Domain-specific rate limiting module
"""

import asyncio
import logging
import random
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .rate_limit_config import RateLimitConfig

logger = logging.getLogger(__name__)


class DomainLimiter:
    """Rate limiter for specific domains"""
    
    def __init__(self, domain: str, config: RateLimitConfig):
        self.domain = domain
        self.config = config
        
        # Request tracking
        self.request_times = deque()
        self.hourly_requests = deque()
        self.burst_requests = deque()
        
        # State tracking
        self.current_delay = config.base_delay
        self.consecutive_failures = 0
        self.last_request_time = 0
        
        # Statistics
        self.total_requests = 0
        self.total_delays = 0
        self.total_failures = 0
    
    async def wait_if_needed(self) -> float:
        """Wait if rate limit would be exceeded"""
        current_time = time.time()
        
        # Clean old requests
        self._clean_old_requests(current_time)
        
        # Check if we need to wait
        wait_time = self._calculate_wait_time(current_time)
        
        if wait_time > 0:
            logger.info(f"⏳ Rate limiting {self.domain}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            self.total_delays += wait_time
        
        # Record this request
        self.request_times.append(current_time)
        self.hourly_requests.append(current_time)
        self.burst_requests.append(current_time)
        self.last_request_time = current_time
        self.total_requests += 1
        
        return wait_time
    
    def _clean_old_requests(self, current_time: float):
        """Remove old request timestamps"""
        # Remove requests older than 1 minute
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()
        
        # Remove requests older than 1 hour
        while self.hourly_requests and current_time - self.hourly_requests[0] > 3600:
            self.hourly_requests.popleft()
        
        # Remove requests older than burst window (10 seconds)
        while self.burst_requests and current_time - self.burst_requests[0] > 10:
            self.burst_requests.popleft()
    
    def _calculate_wait_time(self, current_time: float) -> float:
        """Calculate how long to wait before next request"""
        # Check burst limit
        if len(self.burst_requests) >= self.config.burst_limit:
            return 10.0  # Wait 10 seconds for burst limit
        
        # Check requests per minute
        if len(self.request_times) >= self.config.requests_per_minute:
            return 60.0  # Wait 1 minute
        
        # Check requests per hour
        if len(self.hourly_requests) >= self.config.requests_per_hour:
            return 3600.0  # Wait 1 hour
        
        # Apply adaptive delay
        base_delay = self.config.base_delay
        
        # Increase delay based on consecutive failures
        if self.consecutive_failures > 0:
            base_delay *= (self.config.backoff_multiplier ** self.consecutive_failures)
            base_delay = min(base_delay, self.config.max_delay)
        
        # Add jitter
        jitter = random.uniform(*self.config.jitter_range)
        delay = base_delay * jitter
        
        # Ensure minimum delay between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < delay:
            return delay - time_since_last
        
        return 0.0
    
    def record_success(self):
        """Record a successful request"""
        self.consecutive_failures = 0
        self.current_delay = self.config.base_delay
    
    def record_failure(self):
        """Record a failed request"""
        self.consecutive_failures += 1
        self.total_failures += 1
        self.current_delay = min(
            self.current_delay * self.config.backoff_multiplier,
            self.config.max_delay
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            'domain': self.domain,
            'total_requests': self.total_requests,
            'total_delays': self.total_delays,
            'total_failures': self.total_failures,
            'consecutive_failures': self.consecutive_failures,
            'current_delay': self.current_delay,
            'requests_last_minute': len(self.request_times),
            'requests_last_hour': len(self.hourly_requests),
            'burst_requests': len(self.burst_requests)
        }
    
    def reset(self):
        """Reset the limiter state"""
        self.request_times.clear()
        self.hourly_requests.clear()
        self.burst_requests.clear()
        self.consecutive_failures = 0
        self.current_delay = self.config.base_delay
        self.total_requests = 0
        self.total_delays = 0
        self.total_failures = 0
        self.last_request_time = 0
    
    def __str__(self) -> str:
        return f"DomainLimiter(domain={self.domain}, requests={self.total_requests}, failures={self.total_failures})"
    
    def __repr__(self) -> str:
        return self.__str__()





