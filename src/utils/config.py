#!/usr/bin/env python3
"""
Unified configuration loader for BEYONDLINES.

Loads environment variables and JSON config, exposes feature flags and paths.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


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
            "enable_telegram_channels": False,
            "enable_analysis": True,
            "enable_sqlite_cache": False,
            "supabase_enabled": True,
            "research_api_enabled": False,
            # Automation defaults
            "auto_analyze_after_collection": True,
            "auto_rewrite_after_analysis": False,
            # Scheduling stays manual unless explicitly enabled
            "auto_schedule_after_rewrite": False,
            "auto_pipeline_batch_limit": 25,
            # Keep small to move quickly
            "auto_rewrite_posts_per_profile": 3,
            # Post quickly
            "auto_schedule_delay_minutes": 2,
            # Rewriter fast-path controls
            "rewriter_fast_mode": True,
            "rewriter_max_attempts_per_provider": 1,
            # Comma-separated priority order
            "rewriter_provider_order": "mistral,gemini,ollama",
            # Fast mode score thresholds
            "rewriter_min_quality_score": 5.0,
            "rewriter_min_value_score": 5.0,
            "rewriter_min_rewrite_score": 4.0,
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
        except Exception as e:
            logger.error(f"Error: {e}")
            # Non-fatal; keep defaults

    def _apply_env_overrides(self) -> None:
        def env_bool(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return raw.lower() in ("1", "true", "yes", "on")

        def env_int(name: str, default: int) -> int:
            raw = os.getenv(name)
            if raw is None:
                return default
            try:
                return int(raw)
            except ValueError as e:
                logger.error(f"Error parsing {name} as integer: {e}")
                return default

        self.flags["enable_threads"] = env_bool(
            "ENABLE_THREADS", self.flags["enable_threads"]
        )
        self.flags["enable_github_trending"] = env_bool(
            "ENABLE_GITHUB_TRENDING", self.flags["enable_github_trending"]
        )
        self.flags["enable_telegram_channels"] = env_bool(
            "ENABLE_TELEGRAM_CHANNELS", self.flags["enable_telegram_channels"]
        )
        self.flags["enable_analysis"] = env_bool(
            "ENABLE_ANALYSIS", self.flags["enable_analysis"]
        )
        self.flags["enable_sqlite_cache"] = env_bool(
            "ENABLE_SQLITE_CACHE", self.flags["enable_sqlite_cache"]
        )
        self.flags["supabase_enabled"] = env_bool(
            "SUPABASE_ENABLED", self.flags["supabase_enabled"]
        )
        self.flags["research_api_enabled"] = env_bool(
            "RESEARCH_API_ENABLED", self.flags["research_api_enabled"]
        )
        self.flags["auto_analyze_after_collection"] = env_bool(
            "AUTO_ANALYZE_AFTER_COLLECTION", self.flags["auto_analyze_after_collection"]
        )
        self.flags["auto_rewrite_after_analysis"] = env_bool(
            "AUTO_REWRITE_AFTER_ANALYSIS", self.flags["auto_rewrite_after_analysis"]
        )
        self.flags["auto_schedule_after_rewrite"] = env_bool(
            "AUTO_SCHEDULE_AFTER_REWRITE", self.flags["auto_schedule_after_rewrite"]
        )
        self.flags["auto_pipeline_batch_limit"] = env_int(
            "AUTO_PIPELINE_BATCH_LIMIT", self.flags["auto_pipeline_batch_limit"]
        )
        self.flags["auto_rewrite_posts_per_profile"] = env_int(
            "AUTO_REWRITE_POSTS_PER_PROFILE",
            self.flags["auto_rewrite_posts_per_profile"],
        )
        self.flags["auto_schedule_delay_minutes"] = env_int(
            "AUTO_SCHEDULE_DELAY_MINUTES", self.flags["auto_schedule_delay_minutes"]
        )
        # Rewriter fast-path
        self.flags["rewriter_fast_mode"] = env_bool(
            "REWRITER_FAST_MODE", self.flags["rewriter_fast_mode"]
        )
        self.flags["rewriter_max_attempts_per_provider"] = env_int(
            "REWRITER_MAX_ATTEMPTS_PER_PROVIDER",
            self.flags["rewriter_max_attempts_per_provider"],
        )
        provider_order = os.getenv("REWRITER_PROVIDER_ORDER")
        if provider_order:
            self.flags["rewriter_provider_order"] = provider_order
        self.flags["rewriter_min_quality_score"] = env_int(
            "REWRITER_MIN_QUALITY_SCORE", int(self.flags["rewriter_min_quality_score"])
        )
        self.flags["rewriter_min_value_score"] = env_int(
            "REWRITER_MIN_VALUE_SCORE", int(self.flags["rewriter_min_value_score"])
        )
        self.flags["rewriter_min_rewrite_score"] = env_int(
            "REWRITER_MIN_REWRITE_SCORE", int(self.flags["rewriter_min_rewrite_score"])
        )

    def validate_startup_config(self) -> tuple[bool, list[str]]:
        """
        Validate critical configuration at startup.

        Returns:
            (is_valid, list_of_missing_vars)
        """
        missing = []

        # P0: Critical - Supabase is required
        if self.flags.get("supabase_enabled", True):
            if not self.supabase_url or self.supabase_url == "":
                missing.append("SUPABASE_URL")
            if not self.supabase_key and not self.supabase_service_role_key:
                missing.append("SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY")

        # P0: Critical - At least one AI service
        has_mistral = bool(os.getenv("MISTRAL_API_KEY"))
        has_gemini = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        ollama_url_env = os.getenv("OLLAMA_URL")
        has_ollama = bool(ollama_url_env and ollama_url_env.strip())

        if not (has_mistral or has_gemini or has_ollama):
            missing.append("At least one AI service (MISTRAL_API_KEY, GEMINI_API_KEY, or OLLAMA_URL)")

        # P1: Important - Database path validation if SQLite enabled
        if self.flags.get("enable_sqlite_cache", False):
            db_path = os.getenv("SQLITE_DB_PATH", "beyondlines.db")
            db_dir = Path(db_path).parent
            if not db_dir.exists():
                try:
                    db_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    missing.append(f"SQLite path not writable: {db_path} ({e})")

        return (len(missing) == 0, missing)


_config_singleton: "Config | None" = None


def get_config() -> Config:
    global _config_singleton
    if _config_singleton is None:
        _config_singleton = Config()
    return _config_singleton
