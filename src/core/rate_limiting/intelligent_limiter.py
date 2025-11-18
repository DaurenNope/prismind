"""
Intelligent rate limiting system for web scraping
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from .domain_limiter import DomainLimiter
from .rate_limit_config import RateLimitConfig

logger = logging.getLogger(__name__)


class IntelligentRateLimiter:
    """Intelligent rate limiter with domain-specific limits and adaptive delays"""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.domain_limiters: Dict[str, DomainLimiter] = {}
        self.global_stats = {
            "total_requests": 0,
            "total_delays": 0,
            "total_failures": 0,
            "start_time": datetime.now(),
        }

    async def wait_for_domain(self, url: str) -> float:
        """Wait for a specific domain if rate limit would be exceeded"""
        domain = self._extract_domain(url)

        if domain not in self.domain_limiters:
            self.domain_limiters[domain] = DomainLimiter(domain, self.config)

        wait_time = await self.domain_limiters[domain].wait_if_needed()
        self.global_stats["total_requests"] += 1
        self.global_stats["total_delays"] += wait_time

        return wait_time

    def record_success(self, url: str):
        """Record a successful request for a domain"""
        domain = self._extract_domain(url)
        if domain in self.domain_limiters:
            self.domain_limiters[domain].record_success()

    def record_failure(self, url: str):
        """Record a failed request for a domain"""
        domain = self._extract_domain(url)
        if domain in self.domain_limiters:
            self.domain_limiters[domain].record_failure()
            self.global_stats["total_failures"] += 1

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception as e:
            logger.error(f"Error: {e}")
            return "unknown"

    async def rate_limit(self, url: str, func: Callable, *args, **kwargs) -> Any:
        """Apply rate limiting to a function call"""
        # Wait if needed
        await self.wait_for_domain(url)

        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            self.record_success(url)
            return result

        except Exception as e:
            logger.error(f"Error: {e}")
            # Record failure
            self.record_failure(url)
            raise e

    def get_domain_stats(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific domain"""
        if domain in self.domain_limiters:
            return self.domain_limiters[domain].get_stats()
        return None

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all domains"""
        domain_stats = {}
        for domain, limiter in self.domain_limiters.items():
            domain_stats[domain] = limiter.get_stats()

        return {
            "global_stats": self.global_stats,
            "domain_stats": domain_stats,
            "total_domains": len(self.domain_limiters),
        }

    def reset_domain(self, domain: str):
        """Reset rate limiter for a specific domain"""
        if domain in self.domain_limiters:
            self.domain_limiters[domain].reset()

    def reset_all(self):
        """Reset all rate limiters"""
        for limiter in self.domain_limiters.values():
            limiter.reset()
        self.global_stats = {
            "total_requests": 0,
            "total_delays": 0,
            "total_failures": 0,
            "start_time": datetime.now(),
        }

    def get_recommended_delay(self, url: str) -> float:
        """Get recommended delay for a URL without waiting"""
        domain = self._extract_domain(url)
        if domain in self.domain_limiters:
            limiter = self.domain_limiters[domain]
            # This is a simplified version - in practice you'd want more sophisticated logic
            return limiter.current_delay
        return self.config.base_delay

    def is_domain_healthy(self, domain: str) -> bool:
        """Check if a domain is healthy (not rate limited)"""
        if domain in self.domain_limiters:
            limiter = self.domain_limiters[domain]
            return limiter.consecutive_failures < 3
        return True

    def get_unhealthy_domains(self) -> List[str]:
        """Get list of domains that are currently unhealthy"""
        unhealthy = []
        for domain, limiter in self.domain_limiters.items():
            if limiter.consecutive_failures >= 3:
                unhealthy.append(domain)
        return unhealthy

    def __str__(self) -> str:
        return f"IntelligentRateLimiter(domains={len(self.domain_limiters)}, requests={self.global_stats['total_requests']})"

    def __repr__(self) -> str:
        return self.__str__()


def get_rate_limiter(config_file: Optional[str] = None) -> IntelligentRateLimiter:
    """Get a rate limiter instance with optional config file"""
    if config_file and os.path.exists(config_file):
        config = RateLimitConfig.from_file(config_file)
    else:
        config = RateLimitConfig()

    return IntelligentRateLimiter(config)
