#!/usr/bin/env python3
"""
Unified configuration loader for PrisMind.

Loads environment variables and JSON config, exposes feature flags and paths.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv


class Config:
    """
    Central configuration with sane defaults.
    Supabase is primary; SQLite cache is optional.
    """

    def __init__(self) -> None:
        load_dotenv()

        project_root = Path(__file__).resolve().parents[2]
        self.project_root = project_root

        # Default flags
        self.flags: Dict[str, Any] = {
            "enable_threads": False,
            "enable_github_trending": True,
            "enable_telegram_channels": True,
            "enable_analysis": True,
            "enable_sqlite_cache": True,
            "supabase_enabled": True,
            "research_api_enabled": False,
        }

        # Cookie paths (normalized under cookies/)
        self.cookies_dir = project_root / "cookies"
        self.twitter_cookies_path = self.cookies_dir / "twitter.json"
        self.threads_cookies_path = self.cookies_dir / "threads.json"

        # Load JSON config if present
        self._load_json_config(project_root / "config" / "collection.json")

        # Environment overrides
        self._apply_env_overrides()

        # Supabase
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_KEY", "")
        self.supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    def _load_json_config(self, path: Path) -> None:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # Only apply known flags to avoid surprises
                    for key in self.flags.keys():
                        if key in data:
                            self.flags[key] = bool(data[key])
        except Exception:
            # Non-fatal; keep defaults
            pass

    def _apply_env_overrides(self) -> None:
        def env_bool(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return raw.lower() in ("1", "true", "yes", "on")

        self.flags["enable_threads"] = env_bool("ENABLE_THREADS", self.flags["enable_threads"])
        self.flags["enable_github_trending"] = env_bool("ENABLE_GITHUB_TRENDING", self.flags["enable_github_trending"])
        self.flags["enable_telegram_channels"] = env_bool("ENABLE_TELEGRAM_CHANNELS", self.flags["enable_telegram_channels"])
        self.flags["enable_analysis"] = env_bool("ENABLE_ANALYSIS", self.flags["enable_analysis"])
        self.flags["enable_sqlite_cache"] = env_bool("ENABLE_SQLITE_CACHE", self.flags["enable_sqlite_cache"])
        self.flags["supabase_enabled"] = env_bool("SUPABASE_ENABLED", self.flags["supabase_enabled"])
        self.flags["research_api_enabled"] = env_bool("RESEARCH_API_ENABLED", self.flags["research_api_enabled"])


_config_singleton: "Config | None" = None


def get_config() -> Config:
    global _config_singleton
    if _config_singleton is None:
        _config_singleton = Config()
    return _config_singleton


