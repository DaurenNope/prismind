#!/usr/bin/env python3
"""
Database Monitoring Module

Handles monitoring of collection freshness and stale collection detection.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseMonitoring:
    """Handles database monitoring and alerting"""

    def __init__(self, get_collection_metrics_fn=None):
        self._get_collection_metrics = get_collection_metrics_fn

    def detect_stale_collections(
        self, thresholds_minutes: Optional[Dict[str, int]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Detect stale collections based on last run time"""
        thresholds = thresholds_minutes or {
            "twitter": 180,
            "reddit": 180,
            "threads": 180,
        }
        stale: Dict[str, Dict[str, Any]] = {}
        now = datetime.utcnow()
        for plat, mins in thresholds.items():
            m = (
                self._get_collection_metrics(plat)
                if self._get_collection_metrics
                else {}
            )
            last = m.get("last_run_at") if m else None
            last_dt = None
            if isinstance(last, str):
                try:
                    last_dt = datetime.fromisoformat(last.replace("Z", ""))
                except Exception as e:
                    logger.error(f"Error: {e}")
                    last_dt = None
            age_min = (now - last_dt).total_seconds() / 60 if last_dt else float("inf")
            if age_min > mins:
                stale[plat] = {
                    "age_minutes": int(age_min),
                    "threshold": mins,
                    "metrics": m,
                }
        return stale

    def notify_stale(self, stale: Dict[str, Dict[str, Any]]) -> None:
        """Notify about stale collections via Telegram or logs"""
        if not stale:
            return
        try:
            lines = ["⚠️ Collection stale:"] + [
                f" - {k}: {v['age_minutes']}m (> {v['threshold']}m)"
                for k, v in stale.items()
            ]
            message = "\n".join(lines)

            # Try Telegram first if configured
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv(
                "TELEGRAM_ADMIN_CHAT_ID"
            )
            if token and chat_id:
                try:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    payload = {"chat_id": chat_id, "text": message}
                    requests.post(url, json=payload, timeout=10)
                except Exception as e:
                    logger.warning(f"Failed to send Telegram notification: {e}")
                    logger.warning(message)
            else:
                # Fallback to logs
                logger.warning(message)
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
