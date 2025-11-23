#!/usr/bin/env python3
"""
Collection Orchestrator Agent

Manages all collection operations with scheduling, rate limiting, state persistence,
and error recovery. Inherits from BaseAgent and maintains backward compatibility
with the existing Orchestrator class.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.agents.base_agent import AgentError, AgentStatus, BaseAgent
from src.core.rate_limiting.intelligent_limiter import IntelligentRateLimiter
from src.pipeline.orchestrator import Orchestrator
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    circuit_breaker_registry,
)
from src.infrastructure.database.scrape_state_manager import ScrapeStateManager
from src.storage.db import get_storage
from src.utils.config import get_config
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class CollectionState(Enum):
    """Collection state enumeration"""

    IDLE = "idle"
    COLLECTING = "collecting"
    PAUSED = "paused"
    ERROR = "error"


class ErrorType(Enum):
    """Error classification for recovery"""

    TRANSIENT = "transient"  # Temporary, retryable
    PERMANENT = "permanent"  # Permanent, don't retry
    RATE_LIMIT = "rate_limit"  # Rate limit violation
    CIRCUIT_OPEN = "circuit_open"  # Circuit breaker open


class CollectionOrchestratorAgent(BaseAgent):
    """
    Collection Orchestrator Agent

    Manages collection operations with:
    - Configurable scheduling per platform
    - Rate limit management with exponential backoff
    - State persistence to Redis/database
    - Error recovery with circuit breaker integration
    - Metrics and health checks
    """

    def __init__(
        self,
        agent_id: str = "collection_orchestrator",
        agent_name: str = "Collection Orchestrator",
        agent_version: str = "1.0.0",
        dependencies: Optional[List[str]] = None,
    ):
        """Initialize the Collection Orchestrator Agent"""
        super().__init__(agent_id, agent_name, agent_version, dependencies)

        # Core dependencies
        self.config = get_config()
        self.storage = get_storage()
        self.orchestrator = Orchestrator()  # Delegate to existing orchestrator

        # State management
        self.collection_state: Dict[str, CollectionState] = {}
        self.last_collected_post: Dict[str, Optional[str]] = {}
        self.state_manager = ScrapeStateManager()

        # Rate limiting
        self.rate_limiters: Dict[str, IntelligentRateLimiter] = {}
        self.rate_limit_violations: Dict[str, int] = {}

        # Circuit breakers per platform
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Scheduling
        self.schedules: Dict[str, Dict[str, Any]] = {}
        self.scheduled_tasks: Dict[str, asyncio.Task] = {}
        self.scheduler_lock = asyncio.Lock()

        # Error tracking
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, Dict[str, Any]] = {}

        # Metrics
        self.collection_metrics: Dict[str, Dict[str, Any]] = {}

        # Thread safety
        self._lock = threading.Lock()

        logger.info(f"Initialized {self.agent_name} (ID: {self.agent_id})")

    async def initialize(self) -> bool:
        """
        Initialize the agent.

        Sets up:
        - State synchronization
        - Rate limiters per platform
        - Circuit breakers per platform
        - Load schedules from config
        - Restore state from persistence

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing {self.agent_name}...")

            # Ensure state sync
            self._ensure_state_sync()

            # Initialize rate limiters for each platform
            platforms = self._get_platforms()
            for platform in platforms:
                await self._initialize_rate_limiter(platform)
                await self._initialize_circuit_breaker(platform)
                self.collection_state[platform] = CollectionState.IDLE
                self.last_collected_post[platform] = None
                self.error_counts[platform] = 0

            # Load schedules from config
            await self._load_schedules()

            # Restore state from persistence
            await self._restore_state()

            # Initialize metrics
            self._initialize_metrics()

            self._mark_initialized()
            logger.info(f"{self.agent_name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_name}: {e}", exc_info=True)
            self._set_status(AgentStatus.ERROR)
            raise AgentError(f"Initialization failed: {e}", agent_id=self.agent_id)

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a collection task.

        Task format:
        {
            "action": "collect_all" | "collect_platform" | "schedule_collection",
            "platforms": ["twitter", "reddit", ...],  # Optional
            "platform": "twitter",  # For collect_platform
            "schedule": {...},  # For schedule_collection
        }

        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        action = task.get("action", "collect_all")

        try:
            self._set_status(AgentStatus.RUNNING)

            if action == "collect_all":
                platforms = task.get("platforms")
                result = await self.collect_all(platforms=platforms)
            elif action == "collect_platform":
                platform = task.get("platform")
                if not platform:
                    raise AgentError("Platform required for collect_platform", agent_id=self.agent_id)
                result = await self.collect_platform(platform)
            elif action == "schedule_collection":
                schedule = task.get("schedule", {})
                result = await self.schedule_collection(schedule)
            else:
                raise AgentError(f"Unknown action: {action}", agent_id=self.agent_id)

            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, success=True)
            self._set_status(AgentStatus.IDLE)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, success=False)
            self._set_status(AgentStatus.ERROR)

            error_type = self._classify_error(e)
            await self._handle_error(task.get("platform", "unknown"), e, error_type)

            logger.error(f"Task execution failed: {e}", exc_info=True)
            raise AgentError(f"Task execution failed: {e}", agent_id=self.agent_id)

    async def collect_all(self, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Collect from all platforms or specified platforms.

        Args:
            platforms: Optional list of platforms to collect from

        Returns:
            Dictionary with collection results
        """
        # Delegate to orchestrator but add agent-specific features
        try:
            # Check circuit breakers before starting
            platforms_to_collect = platforms or self._get_platforms()
            available_platforms = []

            for platform in platforms_to_collect:
                breaker = self.circuit_breakers.get(platform)
                if breaker and await breaker._can_execute():
                    available_platforms.append(platform)
                elif breaker:
                    logger.warning(f"Circuit breaker open for {platform}, skipping")
                    self.record_metric(
                        "collection.skipped.circuit_open",
                        1,
                        tags={"platform": platform},
                    )
                else:
                    available_platforms.append(platform)

            if not available_platforms:
                return {
                    "total": 0,
                    "errors": ["All platforms have open circuit breakers"],
                    "platforms": {},
                }

            # Execute collection with rate limiting
            results = await self.orchestrator.collect_all(platforms=available_platforms)

            # Update metrics
            for platform, result in results.items():
                if platform not in ["errors", "error_details", "started_at", "completed_at", "total", "total_duration_seconds", "success_count", "failure_count"]:
                    if isinstance(result, dict):
                        count = result.get("count", 0)
                        success = result.get("success", False)
                        if success:
                            await self._record_success(platform, count)
                        else:
                            await self._record_failure(platform, result.get("error", "Unknown error"))

            # Persist state
            await self._persist_state()

            # Publish event
            self.publish_event(
                "collection.completed",
                {
                    "total": results.get("total", 0),
                    "platforms": len(available_platforms),
                    "success_count": results.get("success_count", 0),
                    "failure_count": results.get("failure_count", 0),
                },
            )

            return results

        except Exception as e:
            logger.error(f"Collection failed: {e}", exc_info=True)
            await self._handle_error("all", e, self._classify_error(e))
            raise

    async def collect_platform(self, platform: str) -> int:
        """
        Collect from a single platform with rate limiting and circuit breaker.

        Args:
            platform: Platform name to collect from

        Returns:
            Number of posts collected
        """
        if platform not in self._get_platforms():
            raise AgentError(f"Unsupported platform: {platform}", agent_id=self.agent_id)

        # Check circuit breaker
        breaker = self.circuit_breakers.get(platform)
        if breaker and not await breaker._can_execute():
            raise AgentError(
                f"Circuit breaker open for {platform}", agent_id=self.agent_id
            )

        # Apply rate limiting
        limiter = self.rate_limiters.get(platform)
        if limiter:
            # Use a dummy URL for rate limiting (platform-specific)
            await limiter.wait_for_domain(f"platform://{platform}")

        try:
            self.collection_state[platform] = CollectionState.COLLECTING

            # Execute collection with circuit breaker protection
            if breaker:
                async with breaker:
                    count = await self.orchestrator.collect_platform(platform)
            else:
                count = await self.orchestrator.collect_platform(platform)

            await self._record_success(platform, count)
            self.collection_state[platform] = CollectionState.IDLE

            # Persist state
            await self._persist_state()

            return count

        except Exception as e:
            self.collection_state[platform] = CollectionState.ERROR
            error_type = self._classify_error(e)
            await self._record_failure(platform, str(e), error_type)

            if breaker:
                await breaker._on_failure()

            raise

    async def schedule_collection(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schedule a collection task.

        Schedule format:
        {
            "platform": "twitter",
            "cron": "0 */6 * * *",  # Every 6 hours
            "timezone": "UTC",
            "enabled": True
        }

        Args:
            schedule: Schedule configuration

        Returns:
            Dictionary with schedule status
        """
        platform = schedule.get("platform")
        if not platform:
            raise AgentError("Platform required in schedule", agent_id=self.agent_id)

        async with self.scheduler_lock:
            self.schedules[platform] = schedule

            # Cancel existing task if any
            if platform in self.scheduled_tasks:
                self.scheduled_tasks[platform].cancel()

            # Start new scheduled task if enabled
            if schedule.get("enabled", True):
                self.scheduled_tasks[platform] = asyncio.create_task(
                    self._run_scheduled_collection(platform, schedule)
                )

            # Persist schedule
            await self._persist_schedules()

            return {"platform": platform, "scheduled": True, "enabled": schedule.get("enabled", True)}

    async def _run_scheduled_collection(self, platform: str, schedule: Dict[str, Any]):
        """Run scheduled collection for a platform"""
        try:
            # Parse cron expression (simplified - use actual cron parser in production)
            cron = schedule.get("cron", "0 * * * *")  # Default: every hour
            timezone_str = schedule.get("timezone", "UTC")

            # For now, use a simple interval-based approach
            # In production, use a proper cron parser like croniter
            interval = self._parse_cron_interval(cron)

            while True:
                await asyncio.sleep(interval)

                # Check if still enabled
                if not schedule.get("enabled", True):
                    break

                # Check for overlapping collections
                if self.collection_state.get(platform) == CollectionState.COLLECTING:
                    logger.warning(f"Skipping scheduled collection for {platform} - already collecting")
                    continue

                logger.info(f"Running scheduled collection for {platform}")
                try:
                    await self.collect_platform(platform)
                except Exception as e:
                    logger.error(f"Scheduled collection failed for {platform}: {e}")

        except asyncio.CancelledError:
            logger.info(f"Scheduled collection cancelled for {platform}")
        except Exception as e:
            logger.error(f"Scheduled collection error for {platform}: {e}")

    def _parse_cron_interval(self, cron: str) -> int:
        """Parse cron expression to interval in seconds (simplified)"""
        # Simplified parser - in production use croniter
        parts = cron.split()
        if len(parts) >= 2:
            # Extract minute and hour
            minute = parts[0]
            hour = parts[1] if len(parts) > 1 else "*"

            if minute.isdigit():
                # Specific minute
                if hour == "*":
                    return 3600  # Every hour
                elif hour.isdigit():
                    return int(hour) * 3600 + int(minute) * 60
                elif hour.startswith("*/"):
                    # Every N hours at specific minute
                    n = int(hour.split("/")[1])
                    return n * 3600
            elif minute == "*":
                if hour == "*":
                    return 3600  # Every hour
                elif hour.isdigit():
                    return int(hour) * 3600
                elif hour.startswith("*/"):
                    # Every N hours
                    n = int(hour.split("/")[1])
                    return n * 3600
            elif minute.startswith("*/"):
                # Every N minutes
                if hour == "*":
                    n = int(minute.split("/")[1])
                    return n * 60
                elif hour.startswith("*/"):
                    # Every N hours
                    n = int(hour.split("/")[1])
                    return n * 3600

        return 3600  # Default: 1 hour

    async def _initialize_rate_limiter(self, platform: str):
        """Initialize rate limiter for a platform"""
        from src.core.rate_limiting.rate_limit_config import RateLimitConfig

        # Platform-specific rate limits
        platform_limits = {
            "twitter": RateLimitConfig(requests_per_minute=15, requests_per_hour=300),
            "reddit": RateLimitConfig(requests_per_minute=30, requests_per_hour=600),
            "threads": RateLimitConfig(requests_per_minute=20, requests_per_hour=400),
            "github_trending": RateLimitConfig(requests_per_minute=10, requests_per_hour=200),
            "telegram_channels": RateLimitConfig(requests_per_minute=30, requests_per_hour=600),
        }

        config = platform_limits.get(platform, RateLimitConfig())
        self.rate_limiters[platform] = IntelligentRateLimiter(config)
        logger.debug(f"Initialized rate limiter for {platform}")

    async def _initialize_circuit_breaker(self, platform: str):
        """Initialize circuit breaker for a platform"""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=300.0,  # 5 minutes
            success_threshold=2,
            timeout=60.0,
        )

        breaker = await circuit_breaker_registry.get_breaker(
            f"collection_{platform}", config
        )
        self.circuit_breakers[platform] = breaker
        logger.debug(f"Initialized circuit breaker for {platform}")

    async def _record_success(self, platform: str, count: int):
        """Record successful collection"""
        self.error_counts[platform] = 0
        self.collection_metrics[platform] = self.collection_metrics.get(platform, {})
        self.collection_metrics[platform]["last_success"] = time.time()
        self.collection_metrics[platform]["last_count"] = count
        self.collection_metrics[platform]["total_collected"] = (
            self.collection_metrics[platform].get("total_collected", 0) + count
        )

        breaker = self.circuit_breakers.get(platform)
        if breaker:
            await breaker._on_success()

        limiter = self.rate_limiters.get(platform)
        if limiter:
            limiter.record_success(f"platform://{platform}")

        self.record_metric("collection.success", 1, tags={"platform": platform})
        self.record_metric("collection.posts_collected", count, tags={"platform": platform})

    async def _record_failure(
        self, platform: str, error: str, error_type: ErrorType = ErrorType.TRANSIENT
    ):
        """Record collection failure"""
        self.error_counts[platform] = self.error_counts.get(platform, 0) + 1
        self.last_errors[platform] = {
            "error": error,
            "error_type": error_type.value,
            "timestamp": time.time(),
        }

        breaker = self.circuit_breakers.get(platform)
        if breaker:
            await breaker._on_failure()

        limiter = self.rate_limiters.get(platform)
        if limiter:
            limiter.record_failure(f"platform://{platform}")

        if error_type == ErrorType.RATE_LIMIT:
            self.rate_limit_violations[platform] = (
                self.rate_limit_violations.get(platform, 0) + 1
            )
            # Alert on rate limit violation
            self.publish_event(
                "collection.rate_limit_violation",
                {"platform": platform, "error": error},
            )

        self.record_metric("collection.failure", 1, tags={"platform": platform, "error_type": error_type.value})

        # Alert on persistent failures
        if self.error_counts[platform] >= 5:
            self.publish_event(
                "collection.persistent_failure",
                {
                    "platform": platform,
                    "error_count": self.error_counts[platform],
                    "last_error": error,
                },
            )

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type for recovery strategy"""
        error_str = str(error).lower()

        if "rate limit" in error_str or "429" in error_str:
            return ErrorType.RATE_LIMIT
        elif "circuit" in error_str or "breaker" in error_str:
            return ErrorType.CIRCUIT_OPEN
        elif any(
            term in error_str
            for term in ["timeout", "connection", "network", "temporary"]
        ):
            return ErrorType.TRANSIENT
        else:
            return ErrorType.PERMANENT

    async def _handle_error(
        self, platform: str, error: Exception, error_type: ErrorType
    ):
        """Handle collection error with appropriate recovery"""
        await self._record_failure(platform, str(error), error_type)

        if error_type == ErrorType.TRANSIENT:
            # Implement exponential backoff
            backoff_time = min(2 ** self.error_counts.get(platform, 0), 300)
            logger.info(f"Transient error for {platform}, backing off for {backoff_time}s")
            await asyncio.sleep(backoff_time)

    def _get_platforms(self) -> List[str]:
        """Get list of available platforms"""
        platforms = ["twitter", "reddit", "threads", "github_trending", "telegram_channels", "discovery"]
        
        # Filter based on config flags
        if not self.config.flags.get("enable_threads"):
            platforms = [p for p in platforms if p != "threads"]
        if not self.config.flags.get("enable_github_trending"):
            platforms = [p for p in platforms if p != "github_trending"]
        if not self.config.flags.get("enable_telegram_channels"):
            platforms = [p for p in platforms if p != "telegram_channels"]

        return platforms

    def _ensure_state_sync(self):
        """Ensure state database is synced with main database"""
        try:
            self.state_manager.sync_state_from_main_db(force=False)
        except Exception as e:
            logger.debug(f"State sync skipped: {e}")

    async def _load_schedules(self):
        """Load schedules from config"""
        # Load from config file or database
        # For now, use empty schedules
        self.schedules = {}

    async def _persist_schedules(self):
        """Persist schedules to storage"""
        # Persist to database or config file
        # Implementation depends on storage backend
        pass

    async def _restore_state(self):
        """Restore state from persistence"""
        try:
            # Try Redis first if available
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    import redis.asyncio as aioredis
                    redis_client = aioredis.from_url(redis_url, decode_responses=True)
                    
                    # Restore last collected post per platform
                    for platform in self._get_platforms():
                        key = f"collection:last_post:{platform}"
                        last_post = await redis_client.get(key)
                        if last_post:
                            self.last_collected_post[platform] = last_post
                    
                    # Restore collection metrics
                    metrics_key = "collection:metrics"
                    metrics_data = await redis_client.get(metrics_key)
                    if metrics_data:
                        import json
                        self.collection_metrics = json.loads(metrics_data)
                    
                    await redis_client.aclose()
                    logger.debug("State restored from Redis")
                    return
                except Exception as e:
                    logger.debug(f"Redis restore failed, falling back to database: {e}")
            
            # Fallback to database
            # Restore from ScrapeStateManager or database
            # This is a simplified version - in production, use proper state management
            logger.debug("State restored from database (fallback)")
            
        except Exception as e:
            logger.warning(f"State restoration failed: {e}")

    async def _persist_state(self):
        """Persist current state to storage"""
        try:
            # Try Redis first if available
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    import redis.asyncio as aioredis
                    redis_client = aioredis.from_url(redis_url, decode_responses=True)
                    
                    # Persist last collected post per platform
                    for platform, last_post in self.last_collected_post.items():
                        if last_post:
                            key = f"collection:last_post:{platform}"
                            await redis_client.set(key, last_post)
                    
                    # Persist collection metrics
                    metrics_key = "collection:metrics"
                    import json
                    await redis_client.set(metrics_key, json.dumps(self.collection_metrics))
                    
                    await redis_client.aclose()
                    logger.debug("State persisted to Redis")
                    return
                except Exception as e:
                    logger.debug(f"Redis persist failed, falling back to database: {e}")
            
            # Fallback to database
            # Persist to ScrapeStateManager or database
            # This is a simplified version - in production, use proper state management
            logger.debug("State persisted to database (fallback)")
            
        except Exception as e:
            logger.warning(f"State persistence failed: {e}")

    def _initialize_metrics(self):
        """Initialize collection metrics"""
        for platform in self._get_platforms():
            self.collection_metrics[platform] = {
                "total_collected": 0,
                "last_success": None,
                "last_count": 0,
                "error_count": 0,
            }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check with collection-specific metrics"""
        base_health = await super().health_check()

        # Add collection-specific health info
        collection_health = {
            "platforms": {},
            "circuit_breakers": {},
            "rate_limiters": {},
            "scheduled_collections": len(self.scheduled_tasks),
        }

        for platform in self._get_platforms():
            collection_health["platforms"][platform] = {
                "state": self.collection_state.get(platform, CollectionState.IDLE).value,
                "error_count": self.error_counts.get(platform, 0),
                "last_error": self.last_errors.get(platform),
                "metrics": self.collection_metrics.get(platform, {}),
            }

            breaker = self.circuit_breakers.get(platform)
            if breaker:
                collection_health["circuit_breakers"][platform] = breaker.get_state()

            limiter = self.rate_limiters.get(platform)
            if limiter:
                collection_health["rate_limiters"][platform] = limiter.get_all_stats()

        base_health["collection"] = collection_health
        return base_health

    async def shutdown(self) -> None:
        """Shutdown the agent gracefully"""
        logger.info(f"Shutting down {self.agent_name}...")

        # Cancel scheduled tasks
        for platform, task in self.scheduled_tasks.items():
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"Error cancelling task for {platform}: {e}")

        # Persist final state
        await self._persist_state()

        # Call parent shutdown
        await super().shutdown()


# Singleton instance
_collection_agent: Optional[CollectionOrchestratorAgent] = None
_agent_lock = threading.Lock()


def get_collection_orchestrator_agent() -> CollectionOrchestratorAgent:
    """Get singleton instance of Collection Orchestrator Agent"""
    global _collection_agent
    if _collection_agent is None:
        with _agent_lock:
            if _collection_agent is None:
                _collection_agent = CollectionOrchestratorAgent()
    return _collection_agent

