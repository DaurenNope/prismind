"""
Social Media Interaction Cache with State Management
Provides persistent storage and state tracking for social interactions
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..messaging.message_queue import MessageQueue, QueueConfig
from ..utils.exceptions import CacheError, StateError

logger = logging.getLogger(__name__)


class CacheEntryStatus(Enum):
    """Status of cache entries"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class CacheEntry:
    """Cache entry for social interaction"""

    key: str
    data: Dict[str, Any]
    status: CacheEntryStatus = CacheEntryStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return self.expires_at is not None and time.time() > self.expires_at

    def touch(self):
        """Update access statistics"""
        self.access_count += 1
        self.last_accessed = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "key": self.key,
            "data": self.data,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "tags": list(self.tags),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary"""
        data["tags"] = set(data.get("tags", []))
        data["status"] = CacheEntryStatus(data.get("status", "active"))
        return cls(**data)


@dataclass
class StateSnapshot:
    """Snapshot of system state at a point in time"""

    timestamp: float
    platform_states: Dict[str, Dict[str, Any]]
    queue_states: Dict[str, Dict[str, Any]]
    cache_stats: Dict[str, Any]
    total_interactions: int
    processed_interactions: int
    failed_interactions: int


class SocialCache:
    """
    High-performance cache for social media interactions with state management
    Uses Redis for persistence and local cache for performance
    """

    def __init__(self, redis_url: str, max_memory_mb: int = 100):
        self.redis_url = redis_url
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._redis = None
        self._local_cache: Dict[str, CacheEntry] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._state_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

        # Cache configuration
        self.default_ttl = 3600  # 1 hour
        self.max_local_entries = 10000
        self.cleanup_interval = 300  # 5 minutes

    async def initialize(self):
        """Initialize cache connection"""
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self.redis_url)
            await self._redis.ping()
            logger.info("Social cache initialized")
        except Exception as e:
            logger.error(f"Error: {e}")
            raise CacheError(f"Failed to initialize social cache: {e}")

        # Start background tasks
        self._running = True
        asyncio.create_task(self._cleanup_loop())
        asyncio.create_task(self._state_persistence_loop())

    async def stop(self):
        """Stop cache and cleanup"""
        self._running = False
        if self._redis:
            await self._redis.close()
        logger.info("Social cache stopped")

    async def get(self, key: str, default: Any = None) -> Optional[Dict[str, Any]]:
        """Get cached data"""
        # Check local cache first
        if key in self._local_cache:
            entry = self._local_cache[key]
            if not entry.is_expired() and entry.status == CacheEntryStatus.ACTIVE:
                entry.touch()
                self._cache_hits += 1
                return entry.data.copy()
            else:
                # Remove expired or inactive entry
                del self._local_cache[key]

        # Check Redis cache
        try:
            cached_data = await self._redis.get(f"social_cache:{key}")
            if cached_data:
                entry_data = json.loads(cached_data)
                entry = CacheEntry.from_dict(entry_data)

                if not entry.is_expired() and entry.status == CacheEntryStatus.ACTIVE:
                    # Add to local cache if space allows
                    if len(self._local_cache) < self.max_local_entries:
                        self._local_cache[key] = entry
                    entry.touch()
                    self._cache_hits += 1
                    return entry.data.copy()

        except Exception as e:
            logger.error(f"Error getting from cache: {e}")

        self._cache_misses += 1
        return default

    async def set(
        self,
        key: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Set cached data"""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else None

        entry = CacheEntry(
            key=key,
            data=data,
            expires_at=expires_at,
            tags=tags or set(),
            metadata=metadata or {},
        )

        # Update local cache
        if len(self._local_cache) >= self.max_local_entries:
            await self._evict_lru_entry()
        self._local_cache[key] = entry

        # Update Redis cache
        try:
            cache_key = f"social_cache:{key}"
            serialized_data = json.dumps(entry.to_dict())

            await self._redis.setex(cache_key, ttl, serialized_data)

            # Add to tag indexes
            if tags:
                for tag in tags:
                    await self._redis.sadd(f"social_cache_tags:{tag}", key)
                    await self._redis.expire(f"social_cache_tags:{tag}", ttl)

        except Exception as e:
            logger.error(f"Error setting cache: {e}")

    async def delete(self, key: str):
        """Delete cached data"""
        # Remove from local cache
        if key in self._local_cache:
            entry = self._local_cache[key]
            entry.status = CacheEntryStatus.DELETED
            del self._local_cache[key]

        # Remove from Redis cache
        try:
            # Get entry data for tag cleanup
            cache_key = f"social_cache:{key}"
            cached_data = await self._redis.get(cache_key)
            if cached_data:
                entry_data = json.loads(cached_data)
                entry = CacheEntry.from_dict(entry_data)

                # Remove from tag indexes
                for tag in entry.tags:
                    await self._redis.srem(f"social_cache_tags:{tag}", key)

            # Delete main cache entry
            await self._redis.delete(cache_key)

        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")

    async def get_by_tags(
        self, tags: Set[str], limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get entries by tags"""
        if not tags:
            return []

        try:
            # Find keys with all specified tags
            tag_keys = [f"social_cache_tags:{tag}" for tag in tags]

            if len(tag_keys) == 1:
                matching_keys = await self._redis.smembers(tag_keys[0])
            else:
                # Intersection of multiple tag sets
                matching_keys = await self._redis.sinter(*tag_keys)

            # Get actual data for matching keys
            results = []
            for key in matching_keys:
                if len(results) >= limit:
                    break

                data = await self.get(key.decode() if isinstance(key, bytes) else key)
                if data:
                    results.append(data)

            return results

        except Exception as e:
            logger.error(f"Error getting by tags: {e}")
            return []

    async def invalidate_tags(self, tags: Set[str]):
        """Invalidate all entries with specified tags"""
        for tag in tags:
            try:
                tag_key = f"social_cache_tags:{tag}"
                keys = await self._redis.smembers(tag_key)

                for key in keys:
                    await self.delete(key.decode() if isinstance(key, bytes) else key)

                await self._redis.delete(tag_key)

            except Exception as e:
                logger.error(f"Error invalidating tag {tag}: {e}")

    async def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0

        try:
            redis_info = await self._redis.info("memory")
            redis_memory = redis_info.get("used_memory", 0)
        except Exception as e:
            logger.error(f"Error: {e}")
            redis_memory = 0

        return {
            "local_cache_size": len(self._local_cache),
            "local_cache_max": self.max_local_entries,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "redis_memory_bytes": redis_memory,
            "max_memory_bytes": self.max_memory_bytes,
            "memory_usage_ratio": redis_memory / self.max_memory_bytes
            if self.max_memory_bytes > 0
            else 0,
            "state_queue_size": self._state_queue.qsize(),
            "is_running": self._running,
        }

    async def _evict_lru_entry(self):
        """Evict least recently used entry from local cache"""
        if not self._local_cache:
            return

        # Find LRU entry
        lru_key = min(
            self._local_cache.keys(), key=lambda k: self._local_cache[k].last_accessed
        )
        del self._local_cache[lru_key]

    async def _cleanup_loop(self):
        """Background cleanup of expired entries"""
        while self._running:
            try:
                await self._cleanup_expired()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)

    async def _cleanup_expired(self):
        """Remove expired entries from local cache"""
        current_time = time.time()
        expired_keys = []

        for key, entry in self._local_cache.items():
            if entry.is_expired() or entry.status != CacheEntryStatus.ACTIVE:
                expired_keys.append(key)

        for key in expired_keys:
            del self._local_cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def _state_persistence_loop(self):
        """Background persistence of state changes"""
        while self._running:
            try:
                # Process state changes
                state_changes = []
                while not self._state_queue.empty():
                    try:
                        change = self._state_queue.get_nowait()
                        state_changes.append(change)
                    except asyncio.QueueEmpty:
                        logger.error(f"Error: {e}")
                        break

                if state_changes:
                    await self._persist_state_changes(state_changes)

                await asyncio.sleep(10)  # Process every 10 seconds

            except Exception as e:
                logger.error(f"Error in state persistence loop: {e}")
                await asyncio.sleep(30)

    async def _persist_state_changes(self, state_changes: List[Dict[str, Any]]):
        """Persist state changes to Redis"""
        try:
            for change in state_changes:
                state_key = f"social_state:{change['type']}:{change['id']}"

                # Merge with existing state
                existing = await self._redis.hgetall(state_key)
                if existing:
                    # Convert bytes to strings
                    existing = {k.decode(): v.decode() for k, v in existing.items()}

                # Update with new changes
                existing.update(change.get("data", {}))
                existing["updated_at"] = str(time.time())

                # Store with TTL
                await self._redis.hmset(state_key, existing)
                await self._redis.expire(state_key, 86400)  # 24 hours

        except Exception as e:
            logger.error(f"Error persisting state changes: {e}")

    async def record_state_change(
        self, change_type: str, entity_id: str, data: Dict[str, Any]
    ):
        """Record a state change for persistence"""
        state_change = {
            "type": change_type,
            "id": entity_id,
            "data": data,
            "timestamp": time.time(),
        }

        try:
            await self._state_queue.put(state_change)
        except asyncio.QueueFull:
            logger.warning("State queue full, dropping state change")

    async def get_state(
        self, change_type: str, entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current state for an entity"""
        try:
            state_key = f"social_state:{change_type}:{entity_id}"
            state_data = await self._redis.hgetall(state_key)

            if state_data:
                return {k.decode(): v.decode() for k, v in state_data.items()}

            return None

        except Exception as e:
            logger.error(f"Error getting state: {e}")
            return None

    async def create_state_snapshot(self) -> StateSnapshot:
        """Create a snapshot of current system state"""
        try:
            # Get platform states
            platform_states = {}
            for platform in ["twitter", "threads", "telegram", "reddit"]:
                state = await self.get_state("platform", platform)
                if state:
                    platform_states[platform] = state

            # Get queue states
            queue_states = {}
            for queue_name in ["mentions", "replies", "approvals"]:
                state = await self.get_state("queue", queue_name)
                if state:
                    queue_states[queue_name] = state

            # Get cache stats
            cache_stats = await self.get_statistics()

            # Count interactions
            total_interactions = await self._redis.dbsize()  # Rough estimate

            snapshot = StateSnapshot(
                timestamp=time.time(),
                platform_states=platform_states,
                queue_states=queue_states,
                cache_stats=cache_stats,
                total_interactions=total_interactions,
                processed_interactions=cache_stats.get("cache_hits", 0),
                failed_interactions=cache_stats.get("cache_misses", 0),
            )

            # Store snapshot
            snapshot_key = f"social_snapshot:{int(snapshot.timestamp)}"
            snapshot_data = {
                "timestamp": snapshot.timestamp,
                "platform_states": snapshot.platform_states,
                "queue_states": snapshot.queue_states,
                "cache_stats": snapshot.cache_stats,
                "total_interactions": snapshot.total_interactions,
                "processed_interactions": snapshot.processed_interactions,
                "failed_interactions": snapshot.failed_interactions,
            }

            await self._redis.setex(
                snapshot_key, 86400 * 7, json.dumps(snapshot_data)  # Keep for 7 days
            )

            return snapshot

        except Exception as e:
            logger.error(f"Error creating state snapshot: {e}")
            raise CacheError(f"Failed to create state snapshot: {e}")

    async def restore_from_snapshot(self, snapshot_timestamp: float) -> bool:
        """Restore system state from a snapshot"""
        try:
            snapshot_key = f"social_snapshot:{int(snapshot_timestamp)}"
            snapshot_data = await self._redis.get(snapshot_key)

            if not snapshot_data:
                logger.warning(f"No snapshot found for timestamp {snapshot_timestamp}")
                return False

            snapshot_info = json.loads(snapshot_data)

            # Restore platform states
            for platform, state in snapshot_info.get("platform_states", {}).items():
                state_key = f"social_state:platform:{platform}"
                await self._redis.hmset(state_key, state)
                await self._redis.expire(state_key, 86400)

            # Restore queue states
            for queue, state in snapshot_info.get("queue_states", {}).items():
                state_key = f"social_state:queue:{queue}"
                await self._redis.hmset(state_key, state)
                await self._redis.expire(state_key, 86400)

            logger.info(f"Restored state from snapshot {snapshot_timestamp}")
            return True

        except Exception as e:
            logger.error(f"Error restoring from snapshot: {e}")
            return False

    async def get_recent_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent snapshots"""
        try:
            pattern = "social_snapshot:*"
            keys = await self._redis.keys(pattern)

            snapshots = []
            for key in sorted(keys, reverse=True)[:limit]:
                snapshot_data = await self._redis.get(key)
                if snapshot_data:
                    snapshot_info = json.loads(snapshot_data)
                    snapshots.append(
                        {
                            "timestamp": snapshot_info["timestamp"],
                            "datetime": datetime.fromtimestamp(
                                snapshot_info["timestamp"], timezone.utc
                            ).isoformat(),
                            "total_interactions": snapshot_info["total_interactions"],
                            "cache_stats": snapshot_info["cache_stats"],
                        }
                    )

            return snapshots

        except Exception as e:
            logger.error(f"Error getting recent snapshots: {e}")
            return []


# Global cache instance
social_cache: Optional[SocialCache] = None


async def init_social_cache(redis_url: str, max_memory_mb: int = 100) -> SocialCache:
    """Initialize global social cache"""
    global social_cache
    social_cache = SocialCache(redis_url, max_memory_mb)
    await social_cache.initialize()
    return social_cache


def get_social_cache() -> Optional[SocialCache]:
    """Get global social cache"""
    return social_cache
