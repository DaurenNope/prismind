#!/usr/bin/env python3
"""
Twitter cookie utilities.

Provides a lightweight abstraction around the cookie storage file used by
`TwitterExtractorPlaywright` so that file I/O and validation responsibilities
are separated from the main extractor class.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class TwitterCookieStore:
    """Manage loading, saving, and validating Twitter cookies on disk."""

    def __init__(self, cookie_file: str):
        self.path = Path(cookie_file)

    # -----------------------------
    # Cookie file helpers
    # -----------------------------
    def exists(self) -> bool:
        return self.path.exists()

    def ensure_parent_dir(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # -----------------------------
    # Load / save
    # -----------------------------
    def load(self) -> Optional[List[Dict[str, Any]]]:
        """Load cookies from disk, handling both list and dict formats."""
        if not self.exists():
            return None

        try:
            with self.path.open("r") as f:
                cookie_data = json.load(f)
        except Exception as exc:
            logger.warning("Failed to load cookies from %s: %s", self.path, exc)
            return None

        cookies: List[Dict[str, Any]]
        if isinstance(cookie_data, list):
            cookies = cookie_data
        elif isinstance(cookie_data, dict):
            cookies = cookie_data.get("cookies") or cookie_data.get("data") or []
            if not cookies and cookie_data:
                cookies = [cookie_data]
        else:
            cookies = []

        if cookies:
            # Use f-string for compatibility with structured logger signature
            logger.debug(f"Loaded {len(cookies)} cookies from {self.path}")
            return cookies

        logger.warning("No valid cookies found in %s", self.path)
        return None

    def save(self, cookies: List[Dict[str, Any]]) -> None:
        """
        Persist cookies to disk in Playwright storage_state format:
        {"cookies": [...], "origins": []}
        """
        try:
            self.ensure_parent_dir()
            storage_state = {"cookies": cookies, "origins": []}
            with self.path.open("w") as f:
                json.dump(storage_state, f, indent=2)
            # Use f-string for compatibility with structured logger signature
            logger.debug(f"Saved {len(cookies)} cookies to {self.path} in storage_state format")
        except Exception as exc:
            logger.warning("Failed to save cookies to %s: %s", self.path, exc)

    # -----------------------------
    # Validation / freshness
    # -----------------------------
    def validate(self) -> bool:
        """Check whether the cookie file is a valid Playwright storage_state."""
        if not self.exists():
            return False

        try:
            with self.path.open("r") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            logger.warning("Cookie file %s is not valid JSON: %s", self.path, exc)
            return False
        except Exception as exc:
            logger.warning("Failed to validate cookie file %s: %s", self.path, exc)
            return False

        if not isinstance(data, dict):
            logger.warning(
                "Cookie file %s is not in storage_state format (expected dict)",
                self.path,
            )
            return False

        cookies = data.get("cookies")
        if not isinstance(cookies, list):
            logger.warning(
                "Cookie file %s missing 'cookies' list (found %s)",
                self.path,
                type(cookies).__name__,
            )
            return False

        for cookie in cookies:
            if not isinstance(cookie, dict) or "name" not in cookie or "value" not in cookie:
                logger.warning("Invalid cookie entry detected in %s", self.path)
                return False

        # Use f-string for compatibility with structured logger signature
        logger.debug(f"Validated cookie storage_state at {self.path} with {len(cookies)} cookies")
        return True

    def get_age_seconds(self) -> Optional[float]:
        """Return the age of the cookie file in seconds, if it exists."""
        if not self.exists():
            return None
        try:
            return time.time() - self.path.stat().st_mtime
        except Exception as exc:
            logger.warning("Could not determine age of %s: %s", self.path, exc)
            return None

    def is_fresh(self, max_age_seconds: float) -> bool:
        """Check whether the cookie file is younger than `max_age_seconds`."""
        age = self.get_age_seconds()
        if age is None:
            return False
        return age < max_age_seconds

