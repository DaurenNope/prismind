#!/usr/bin/env python3
"""
Database Repair Module

Handles post repair, incomplete post handling, and platform normalization.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)

_VAR_DIR = Path("var")
_VAR_DIR.mkdir(parents=True, exist_ok=True)
_PLATFORM_FIX_MARKER = _VAR_DIR / "last_platform_fix.txt"
_VALID_PLATFORMS = {
    "twitter",
    "reddit",
    "threads",
    "github",
    "telegram",
    "rss",
    "discovery",
}


class DatabaseRepair:
    """Handles database repair and data quality fixes"""

    def __init__(self, supabase=None, sqlite=None, post_inserter=None):
        self._supabase = supabase
        self._sqlite = sqlite
        self._post_inserter = post_inserter

    def _is_empty(self, v: Any) -> bool:
        """Check if a value is empty"""
        try:
            if v is None:
                return True
            if isinstance(v, str) and not v.strip():
                return True
            if isinstance(v, (list, dict)) and not v:
                return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        return False

    def count_incomplete_posts(self) -> int:
        """Count posts in Supabase missing required fields.
        Required: post_id, platform, url, author_handle, content, created_at, ai_summary,
        value_score, quality_score, language, content_type.
        """
        if self._supabase is None:
            return 0
        try:
            # Using OR across null/empty checks
            q = (
                (
                    self._supabase.table("posts")
                    .select("id", count="exact")
                    .or_(
                        "post_id.is.null,post_id.eq.,"
                        "platform.is.null,platform.eq.,"
                        "url.is.null,url.eq.,"
                        "author_handle.is.null,author_handle.eq.,"
                        "content.is.null,content.eq.,"
                        "created_at.is.null,"
                        "ai_summary.is.null,ai_summary.eq.,"
                        "value_score.is.null,"
                        "quality_score.is.null,"
                        "language.is.null,language.eq.,"
                        "content_type.is.null,content_type.eq."
                    )
                )
                .limit(1)
                .execute()
            )
            return int(getattr(q, "count", 0) or 0)
        except Exception as e:
            logger.error(f"Error: {e}")
            return 0

    def repair_incomplete_posts(self, limit: int = 200) -> int:
        """Fetch incomplete posts and backfill required fields with safe defaults.
        Also normalizes time sensitivity fields.
        Returns number of rows successfully upserted.
        """
        if self._supabase is None or self._post_inserter is None:
            return 0
        try:
            res = (
                self._supabase.table("posts")
                .select("*")
                .or_(
                    "post_id.is.null,post_id.eq.,"
                    "platform.is.null,platform.eq.,"
                    "url.is.null,url.eq.,"
                    "author_handle.is.null,author_handle.eq.,"
                    "content.is.null,content.eq.,"
                    "created_at.is.null,"
                    "ai_summary.is.null,ai_summary.eq.,"
                    "value_score.is.null,"
                    "quality_score.is.null,"
                    "language.is.null,language.eq.,"
                    "content_type.is.null,content_type.eq."
                )
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            items = getattr(res, "data", []) or []
        except Exception as e:
            logger.error(f"Error: {e}")
            items = []

        repaired = 0
        for p in items:
            try:
                fixed = dict(p)
                # Required defaults
                fixed["post_id"] = (
                    p.get("post_id")
                    or (p.get("url", "").split("/")[-1] if p.get("url") else None)
                    or (p.get("id"))
                )
                if not fixed.get("post_id") or not fixed.get("platform"):
                    continue
                fixed["platform"] = (p.get("platform") or "").lower()
                fixed["url"] = p.get("url") or ""
                ah = p.get("author_handle") or (
                    p.get("author", "").split()[0] if p.get("author") else ""
                )
                fixed["author_handle"] = ah
                content = (p.get("content") or "").strip()
                if not content:
                    summary = p.get("ai_summary") or ""
                    fixed["content"] = summary or fixed["url"]
                if self._is_empty(p.get("ai_summary")):
                    fixed["ai_summary"] = (fixed.get("content") or "")[:280]
                if not p.get("analyzed_at"):
                    fixed["analyzed_at"] = datetime.utcnow().isoformat()
                else:
                    fixed["analyzed_at"] = p.get("analyzed_at")
                fixed["language"] = p.get("language") or "en"
                if self._is_empty(p.get("content_type")):
                    fixed["content_type"] = (
                        "thread" if fixed.get("platform") == "threads" else "post"
                    )

                # Scores 0–10
                def _score(v):
                    try:
                        v_float = float(v)
                        return max(0.0, min(10.0, v_float))
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        return 0.0

                fixed["value_score"] = _score(p.get("value_score", 0))
                fixed["quality_score"] = _score(p.get("quality_score", 0))
                # Time sensitivity defaults
                if p.get("time_sensitive") is None:
                    fixed["time_sensitive"] = False
                if p.get("urgency_score") is None:
                    fixed["urgency_score"] = 0.0
                if self._is_empty(p.get("relevance_window")):
                    fixed["relevance_window"] = None
                if fixed.get("time_sensitive_reasons") is None:
                    fixed["time_sensitive_reasons"] = ""

                if self._supabase is None:
                    continue

                if self._post_inserter is not None:
                    mapped = self._post_inserter._map_post_data(fixed, fixed["post_id"])  # type: ignore[attr-defined]
                else:
                    mapped = fixed
                mapped["platform"] = fixed["platform"]
                mapped["post_id"] = fixed["post_id"]
                self._supabase.table("posts").upsert(
                    mapped, on_conflict="platform,post_id"
                ).execute()
                repaired += 1
            except Exception as e:
                logger.error(f"Error: {e}")
                continue
        return repaired

    def _infer_platform(self, post: Dict[str, Any]) -> Optional[str]:
        """Infer platform from post data"""
        platform = (post.get("platform") or "").strip().lower()
        if platform in _VALID_PLATFORMS:
            return platform

        url = (post.get("url") or "").strip().lower()
        post_id = (post.get("post_id") or "").strip().lower()

        if any(domain in url for domain in ["twitter.com", "x.com"]):
            return "twitter"
        if post_id.startswith("twitter_"):
            return "twitter"

        if any(domain in url for domain in ["reddit.com", "redd.it"]):
            return "reddit"
        if post_id.startswith("t3_") or (
            len(post_id) in (6, 7) and post_id.isalnum() and platform == "reddit"
        ):
            return "reddit"

        if "threads.net" in url or post_id.startswith("threads"):
            return "threads"

        if "github.com" in url:
            return "github"

        if any(domain in url for domain in ["t.me", "telegram.me", "telegram.org"]):
            return "telegram"

        # RSS/discovery fallback
        if url.endswith(".xml") or any(
            token in url for token in ["/feed", "?format=rss", "rss."]
        ):
            return "rss"

        if url:
            return "discovery"

        # Fallback: sometimes platform accidentally stores author handle
        if platform.startswith("twitter"):
            return "twitter"
        if platform.startswith("reddit"):
            return "reddit"
        if platform.startswith("threads"):
            return "threads"

        return None

    def fix_invalid_platforms(
        self,
        *,
        limit: int = 2000,
        dry_run: bool = True,
        auto: bool = False,
        interval_minutes: int = 720,
    ) -> Dict[str, Any]:
        """Normalize posts with invalid or blank platform values.

        Args:
            limit: Maximum number of rows to inspect (newest first).
            dry_run: When True, only report potential fixes without applying them.
            auto: If True, respects the interval marker and skips when recently run.
            interval_minutes: Minimum minutes between automatic runs.
        """

        if self._supabase is None:
            return {"updated": 0, "skipped": True, "reason": "Supabase unavailable"}

        if auto:
            try:
                if _PLATFORM_FIX_MARKER.exists():
                    last_run = float(_PLATFORM_FIX_MARKER.read_text().strip())
                    if time.time() - last_run < interval_minutes * 60:
                        return {"updated": 0, "skipped": True, "reason": "recently-ran"}
            except Exception as e:
                logger.error(f"Error: {e}")

        page_size = 500
        inspected = 0
        updates: List[Dict[str, Any]] = []
        unresolved: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        page = 0
        while inspected < limit:
            start = page * page_size
            end = start + page_size - 1
            try:
                response = (
                    self._supabase.table("posts")
                    .select("id,post_id,platform,url,author,author_handle,created_at")
                    .order("created_at", desc=True)
                    .range(start, end)
                    .execute()
                )
            except Exception as fetch_err:
                logger.debug(f"Platform normalization fetch failed: {fetch_err}")
                break

            rows = getattr(response, "data", []) or []
            if not rows:
                break

            for row in rows:
                if inspected >= limit:
                    break
                inspected += 1

                row_id = str(row.get("id")) if row.get("id") is not None else None
                if row_id and row_id in seen_ids:
                    continue
                if row_id:
                    seen_ids.add(row_id)

                raw_platform = (row.get("platform") or "").strip()
                normalized = raw_platform.lower()
                if normalized in _VALID_PLATFORMS:
                    continue

                inferred = self._infer_platform(row)
                if inferred:
                    candidate = {
                        "id": row.get("id"),
                        "post_id": row.get("post_id"),
                        "original_platform": raw_platform,
                        "platform": inferred,
                    }

                    author_handle = (row.get("author_handle") or "").strip()
                    if not author_handle:
                        author = (row.get("author") or "").strip()
                        if inferred == "twitter" and row.get("url"):
                            # Try to parse handle from URL path
                            parts = row["url"].split("/")
                            if len(parts) >= 4:
                                candidate_handle = parts[3]
                                if (
                                    candidate_handle
                                    and not candidate_handle.startswith("status")
                                ):
                                    author_handle = candidate_handle.lstrip("@")
                        if not author_handle and author:
                            author_handle = author.split()[0]
                    if author_handle:
                        candidate["author_handle"] = author_handle.lstrip("@")

                    updates.append(candidate)
                else:
                    unresolved.append(
                        {
                            "post_id": row.get("post_id"),
                            "platform": raw_platform,
                            "url": row.get("url"),
                        }
                    )

            page += 1

        applied = 0
        local_candidates = []

        if self._sqlite is not None:
            try:
                cur = self._sqlite.conn.cursor()
                placeholders = ",".join(["?"] * len(_VALID_PLATFORMS))
                query = f"SELECT * FROM posts WHERE platform IS NULL OR TRIM(platform)='' OR LOWER(platform) NOT IN ({placeholders}) LIMIT ?"
                params = [p for p in _VALID_PLATFORMS] + [limit]
                cur.execute(query, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]

                for row in rows:
                    post = dict(zip(columns, row))
                    inferred = self._infer_platform(post)
                    if inferred:
                        post["platform"] = inferred
                        ah = (post.get("author_handle") or "").strip()
                        if not ah:
                            url = post.get("url") or ""
                            if inferred == "twitter" and url:
                                parts = url.split("/")
                                if (
                                    len(parts) >= 4
                                    and parts[3]
                                    and not parts[3].startswith("status")
                                ):
                                    ah = parts[3].lstrip("@")
                            if not ah and post.get("author"):
                                ah = str(post.get("author")).split()[0]
                        if ah:
                            post["author_handle"] = ah.lstrip("@")
                        local_candidates.append(post)
            except Exception as sqlite_err:
                logger.debug(f"SQLite platform normalization failed: {sqlite_err}")

        if not dry_run:
            for item in updates:
                if not item.get("id"):
                    continue
                payload = {"platform": item["platform"]}
                if item.get("author_handle"):
                    payload["author_handle"] = item["author_handle"]
                try:
                    self._supabase.table("posts").update(payload).eq(
                        "id", item["id"]
                    ).execute()
                    applied += 1
                except Exception as update_err:
                    logger.debug(
                        f"Failed to update platform for {item.get('post_id')}: {update_err}"
                    )
                    continue

                if self._sqlite is not None and item.get("post_id"):
                    try:
                        cur = self._sqlite.conn.cursor()
                        cur.execute(
                            "UPDATE posts SET platform = ?, author_handle = COALESCE(?, author_handle) WHERE post_id = ?",
                            (
                                item["platform"],
                                item.get("author_handle"),
                                item["post_id"],
                            ),
                        )
                        self._sqlite.conn.commit()
                    except Exception as e:
                        logger.error(f"Error: {e}")

        if not dry_run:
            try:
                _PLATFORM_FIX_MARKER.write_text(str(time.time()))
            except Exception as e:
                logger.error(f"Error: {e}")

            if local_candidates:
                cur = self._sqlite.conn.cursor()
                for post in local_candidates:
                    try:
                        cur.execute(
                            "UPDATE posts SET platform = ?, author_handle = COALESCE(?, author_handle) WHERE post_id = ?",
                            (
                                post.get("platform"),
                                post.get("author_handle"),
                                post.get("post_id"),
                            ),
                        )
                    except Exception as update_err:
                        logger.debug(
                            f"Failed to update local platform for {post.get('post_id')}: {update_err}"
                        )
                try:
                    self._sqlite.conn.commit()
                except Exception as e:
                    logger.error(f"Error: {e}")

                if self._post_inserter is not None:
                    for post in local_candidates:
                        try:
                            self._post_inserter.insert_post(post)
                        except Exception as reinserterr:
                            logger.debug(
                                f"Supabase reinsertion failed for {post.get('post_id')}: {reinserterr}"
                            )

        return {
            "inspected": inspected,
            "candidates": len(updates) + len(local_candidates),
            "updated": applied if not dry_run else len(updates) + len(local_candidates),
            "dry_run": dry_run,
            "unresolved": unresolved[:50],
            "skipped": False,
        }
