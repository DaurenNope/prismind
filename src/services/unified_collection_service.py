#!/usr/bin/env python3
"""
UnifiedCollectionService shim backed by the central Orchestrator.

Provides the minimal interface used by the Streamlit Collection tab.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Optional

from src.pipeline.auto_pipeline import AutoPipeline
from src.pipeline.orchestrator import get_orchestrator


class CollectionStatus(str, Enum):
    STARTING = "starting"
    AUTHENTICATING = "authenticating"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CollectionProgress:
    platform: str
    status: CollectionStatus
    current_message: str
    posts_collected: int = 0
    error: Optional[str] = None
    started_at: Optional[float] = None
    updated_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, object]:  # compatibility for tests
        return {
            "platform": self.platform,
            "status": self.status,
            "current_message": self.current_message,
            "posts_collected": self.posts_collected,
            "error": self.error,
        }


@dataclass
class CollectionResult:
    platform: str
    posts_collected: int
    success: bool
    duration_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    posts_analyzed: int = 0  # optional compat field
    posts_failed: int = 0

    def to_dict(self) -> Dict[str, object]:  # compatibility for tests
        return {
            "platform": self.platform,
            "posts_collected": self.posts_collected,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "metadata": self.metadata,
            "posts_analyzed": self.posts_analyzed,
            "posts_failed": self.posts_failed,
        }


class UnifiedCollectionService:
    def __init__(
        self, **kwargs
    ) -> None:  # accept and ignore legacy kwargs like max_retries
        self._collecting: bool = False
        self._stop_requested: bool = False
        self._current_progress: Optional[CollectionProgress] = None
        self._orch = get_orchestrator()
        try:
            auto = AutoPipeline()
            self._auto_pipeline = auto if auto.enabled else None
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ AutoPipeline initialization failed: {e}", exc_info=True)
            self._auto_pipeline = None
        self.SUPPORTED_PLATFORMS = [
            "twitter",
            "reddit",
            "threads",
            "github_trending",
            "telegram_channels",
            "discovery",
        ]

    def get_supported_platforms(self):
        return list(self.SUPPORTED_PLATFORMS)

    async def _collect_from_platform(self, platform: str, limit: int = 50) -> int:
        # thin wrapper for tests to patch; delegates to orchestrator
        return int(await self._orch.collect_platform(platform))

    def is_collecting(self) -> bool:
        return self._collecting

    def get_current_progress(self) -> Optional[CollectionProgress]:
        return self._current_progress

    def stop_collection(self) -> bool:
        """Request to stop the current collection. Returns True if stop was requested, False if not collecting."""
        if self._collecting:
            self._stop_requested = True
            if self._current_progress:
                self._current_progress.status = CollectionStatus.FAILED
                self._current_progress.current_message = "Collection stopped by user"
                self._current_progress.updated_at = datetime.utcnow()
            return True
        return False

    def _check_stop_requested(self) -> bool:
        """Check if stop was requested. Used internally during collection."""
        return self._stop_requested

    async def collect(
        self,
        platform: str,
        progress_callback: Optional[Callable[[CollectionProgress], None]] = None,
    ) -> CollectionResult:
        if self._collecting:
            return CollectionResult(
                platform=platform,
                posts_collected=0,
                success=False,
                error="Collection already in progress",
            )
        self._collecting = True
        self._stop_requested = False  # Reset stop flag
        started = time.time()
        self._current_progress = CollectionProgress(
            platform=platform,
            status=CollectionStatus.STARTING,
            current_message=f"Starting {platform} collection...",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        if progress_callback:
            progress_callback(self._current_progress)

        try:
            # Basic status updates around the orchestrator call
            self._current_progress.status = CollectionStatus.COLLECTING
            self._current_progress.current_message = f"Collecting from {platform}..."
            self._current_progress.updated_at = datetime.utcnow()
            if progress_callback:
                progress_callback(self._current_progress)

            # Retry logic with exponential backoff
            import logging

            from src.utils.retry_handler import retry_async

            logger = logging.getLogger(__name__)

            try:
                count = await retry_async(
                    self._collect_from_platform,
                    platform,
                    50,  # limit
                    max_attempts=3,
                    base_delay=2.0,
                    max_delay=30.0,
                    backoff_factor=2.0,
                    exceptions=(Exception,),
                )
            except Exception as e:
                logger.error(
                    f"❌ Collection failed after retries for {platform}: {e}",
                    exc_info=True,
                )
                raise

            self._current_progress.posts_collected = int(count or 0)
            self._current_progress.status = CollectionStatus.COMPLETED
            self._current_progress.current_message = f"Completed {platform} collection"
            self._current_progress.updated_at = datetime.utcnow()
            self._current_progress.completed_at = datetime.utcnow()
            if progress_callback:
                progress_callback(self._current_progress)

            result = CollectionResult(
                platform=platform,
                posts_collected=self._current_progress.posts_collected,
                success=True,
                duration_seconds=max(0.0, time.time() - started),
            )
            if self._auto_pipeline and self._current_progress.posts_collected:
                try:
                    automation_summary = await self._auto_pipeline.handle_collection(
                        platform, self._current_progress.posts_collected
                    )
                    if automation_summary:
                        result.metadata["automation"] = automation_summary
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"⚠️ Automation pipeline failed for {platform}: {e}",
                        exc_info=True,
                    )
                    # Continue without automation summary - collection was successful
            return result
        except Exception as e:
            logger.error(f"Error: {e}")
            # Check if stop was requested
            if self._stop_requested:
                self._current_progress.status = CollectionStatus.FAILED
                self._current_progress.current_message = "Collection stopped by user"
                self._current_progress.updated_at = datetime.utcnow()
                if progress_callback:
                    progress_callback(self._current_progress)
                return CollectionResult(
                    platform=platform,
                    posts_collected=self._current_progress.posts_collected
                    if self._current_progress
                    else 0,
                    success=False,
                    error="Collection stopped by user",
                    duration_seconds=max(0.0, time.time() - started),
                )
            self._current_progress.status = CollectionStatus.FAILED
            self._current_progress.error = str(e)
            self._current_progress.current_message = f"Failed {platform} collection"
            self._current_progress.updated_at = datetime.utcnow()
            self._current_progress.completed_at = datetime.utcnow()
            if progress_callback:
                progress_callback(self._current_progress)
            return CollectionResult(
                platform=platform,
                posts_collected=self._current_progress.posts_collected
                if self._current_progress
                else 0,
                success=False,
                error=f"Failed: {e}",
                duration_seconds=max(0.0, time.time() - started),
            )
        finally:
            self._collecting = False
            self._stop_requested = False  # Reset stop flag

    async def collect_all(
        self, progress_callback: Optional[Callable[[CollectionProgress], None]] = None
    ) -> Dict[str, CollectionResult]:
        results: Dict[str, CollectionResult] = {}
        for p in self.SUPPORTED_PLATFORMS:
            started = time.time()
            prog = CollectionProgress(
                platform=p,
                status=CollectionStatus.STARTING,
                current_message=f"Starting {p} collection...",
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self._current_progress = prog
            if progress_callback:
                progress_callback(self._current_progress)

            try:
                cnt = await self._collect_from_platform(p, 50)
                results[p] = CollectionResult(
                    platform=p,
                    posts_collected=int(cnt or 0),
                    success=True,
                    duration_seconds=max(0.0, time.time() - started),
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                results[p] = CollectionResult(
                    platform=p,
                    posts_collected=0,
                    success=False,
                    error=f"Failed: {e}",
                    duration_seconds=max(0.0, time.time() - started),
                )
        return results
