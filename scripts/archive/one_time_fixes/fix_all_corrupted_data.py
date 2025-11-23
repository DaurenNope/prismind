#!/usr/bin/env python3
"""
Comprehensive data quality fix script
Fixes all corrupted columns in the database
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import sqlite3
from datetime import datetime

from src.infrastructure.database.database_agent import DatabaseAgent
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def fix_post_data(post_data, db_agent):
    """
    Fix all corrupted fields in a post using DatabaseAgent's normalization.
    This ensures consistency with the live system.
    """
    # Use DatabaseAgent's normalization method (same as live system)
    normalized = db_agent._normalize_post_data(post_data)

    # Check if anything changed
    updated = normalized != post_data

    return normalized, updated


def fix_sqlite_database(limit=None):
    """Fix all corrupted data in SQLite using DatabaseAgent normalization"""
    # Initialize DatabaseAgent for normalization
    try:
        db_agent = DatabaseAgent()
    except Exception as e:
        logger.error(f"Failed to initialize DatabaseAgent: {e}")
        return 0

    db_path = project_root / "beyondlines.db"
    if not db_path.exists():
        logger.error("SQLite database not found")
        return 0

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Find all posts that need fixing
    # Use a broad query - let the normalization logic determine what needs fixing
    query = """
        SELECT * FROM posts
        WHERE
            -- Corrupted created_at (contains text instead of timestamp)
            (created_at IS NOT NULL AND LENGTH(created_at) > 50 AND created_at NOT LIKE '%-%-%' AND created_at NOT LIKE '%/%/%') OR
            -- Corrupted analyzed_at (service name, invalid format, or not a timestamp)
            (analyzed_at IS NOT NULL AND (
                analyzed_at IN ('mistral', 'gemini', 'ollama', 'qwen', 'ai_service', 'unknown', 'none', 'null', '') OR
                analyzed_at NOT LIKE '202%' OR
                LENGTH(analyzed_at) < 10
            )) OR
            -- Missing or corrupted category
            category IS NULL OR category = '' OR category = 'unknown' OR
            category NOT IN ('TECH', 'DATING', 'CRYPTO', 'BUSINESS', 'LEARNING', 'NEWS', 'PERSONAL', 'HEALTH', 'ENTERTAINMENT', 'OTHER', 'DEPRECATED') OR
            -- Any post with a created_at date (let normalization logic determine deprecation)
            (created_at IS NOT NULL AND created_at LIKE '20%') OR
            -- Corrupted best_persona_key
            best_persona_key IN ('evergreen', 'timely', 'trending', 'breaking', 'urgent', 'this-week', 'this-month', 'this-year', 'next-week', 'next-month') OR
            -- Missing best_persona_key when we have analysis
            (best_persona_key IS NULL AND ai_summary IS NOT NULL AND ai_summary != '') OR
            -- String scores that should be numeric
            typeof(rewrite_score) = 'text' OR
            typeof(analysis_confidence) = 'text' OR
            typeof(best_persona_score) = 'text' OR
            typeof(value_score) = 'text' OR
            typeof(quality_score) = 'text' OR
            typeof(urgency_score) = 'text' OR
            -- Missing important fields (only if we have analysis)
            (ai_summary IS NOT NULL AND ai_summary != '' AND (
                rewrite_score IS NULL OR rewrite_score = 0.0 OR
                rewrite_readiness IS NULL OR rewrite_readiness = '' OR
                rewrite_reasons IS NULL OR
                rewrite_risks IS NULL OR
                analysis_confidence IS NULL OR
                analysis_depth IS NULL OR analysis_depth = '' OR
                needs_deep_analysis IS NULL OR
                persona_fit_scores IS NULL OR
                persona_fit_reasons IS NULL OR
                best_persona_score IS NULL OR
                best_persona_reasons IS NULL OR
                time_sensitive IS NULL OR
                urgency_score IS NULL OR
                relevance_window IS NULL OR relevance_window = '' OR
                time_sensitive_reasons IS NULL OR
                value_score IS NULL OR value_score = 0.0 OR
                quality_score IS NULL OR quality_score = 0.0
            ))
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    rows = cur.fetchall()

    if not rows:
        logger.info("✅ No posts need fixing in SQLite")
        conn.close()
        return 0

    logger.info(f"📝 Found {len(rows)} posts needing fixes in SQLite")

    updated_count = 0
    for row in rows:
        post_data = dict(row)

        # Convert JSON strings to Python objects
        for field in [
            "tags",
            "key_concepts",
            "rewrite_reasons",
            "rewrite_risks",
            "best_persona_reasons",
            "persona_fit_scores",
            "persona_fit_reasons",
            "hashtags",
            "mentions",
            "time_sensitive_reasons",
        ]:
            if post_data.get(field) and isinstance(post_data[field], str):
                try:
                    post_data[field] = json.loads(post_data[field])
                except:
                    pass

        # Use DatabaseAgent's normalization (same as live system)
        # This will:
        # - Infer category from content
        # - Map category to persona
        # - Determine if post should be deprecated (based on age and time-sensitivity)
        # - Fix all corrupted fields
        post_data = db_agent._normalize_post_data(post_data)

        # Check if category changed (including deprecation)
        original_category = row["category"] if "category" in row.keys() else None
        new_category = post_data.get("category")
        category_changed = original_category != new_category

        # Always update SQLite if we have analysis data OR if category changed (including deprecation)
        has_analysis = (
            post_data.get("ai_summary") and str(post_data.get("ai_summary", "")).strip()
        )
        should_update = has_analysis or category_changed

        if should_update:
            # Update SQLite
            try:
                # Prepare values
                category_val = post_data.get("category") or None
                persona_key_val = post_data.get("best_persona_key") or None

                result = cur.execute(
                    """
                    UPDATE posts SET
                        created_at = ?,
                        analyzed_at = ?,
                        category = ?,
                        best_persona_key = ?,
                        best_persona_score = ?,
                        rewrite_score = ?,
                        rewrite_readiness = ?,
                        rewrite_reasons = ?,
                        rewrite_risks = ?,
                        analysis_confidence = ?,
                        analysis_depth = ?,
                        needs_deep_analysis = ?,
                        persona_fit_scores = ?,
                        persona_fit_reasons = ?,
                        best_persona_reasons = ?,
                        value_score = ?,
                        quality_score = ?,
                        urgency_score = ?,
                        time_sensitive = ?,
                        relevance_window = ?,
                        time_sensitive_reasons = ?
                    WHERE post_id = ? AND platform = ?
                """,
                    (
                        post_data.get("created_at"),
                        post_data.get("analyzed_at"),
                        category_val,
                        persona_key_val,
                        post_data.get("best_persona_score") or 0.0,
                        post_data.get("rewrite_score") or 0.0,
                        post_data.get("rewrite_readiness") or "",
                        json.dumps(post_data.get("rewrite_reasons", [])),
                        json.dumps(post_data.get("rewrite_risks", [])),
                        post_data.get("analysis_confidence") or 0.7,
                        post_data.get("analysis_depth") or "fast",
                        1 if post_data.get("needs_deep_analysis") else 0,
                        json.dumps(post_data.get("persona_fit_scores", {})),
                        json.dumps(post_data.get("persona_fit_reasons", {})),
                        json.dumps(post_data.get("best_persona_reasons", [])),
                        post_data.get("value_score") or 0.0,
                        post_data.get("quality_score") or 0.0,
                        post_data.get("urgency_score") or 0.0,
                        1 if post_data.get("time_sensitive") else 0,
                        post_data.get("relevance_window") or "evergreen",
                        json.dumps(post_data.get("time_sensitive_reasons", [])),
                        post_data.get("post_id"),
                        post_data.get("platform"),
                    ),
                )
                if result.rowcount > 0:
                    updated_count += 1
                    if updated_count % 10 == 0:
                        logger.info(
                            f"   Progress: {updated_count} posts updated in SQLite"
                        )
            except Exception as e:
                logger.error(
                    f"Failed to update post {post_data.get('post_id')} in SQLite: {e}"
                )
                import traceback

                logger.debug(traceback.format_exc())

    if updated_count > 0:
        conn.commit()
        logger.info(f"✅ Committed {updated_count} SQLite updates")
    conn.close()

    logger.info(f"✅ Fixed {updated_count} posts in SQLite")
    return updated_count


def fix_supabase_database(limit=None):
    """Fix all corrupted data in Supabase using DatabaseAgent normalization and save"""
    try:
        # Initialize DatabaseAgent (handles normalization and saving)
        db_agent = DatabaseAgent()
        if not db_agent._supabase:
            logger.warning(
                "Supabase not available (check environment variables), skipping Supabase fix"
            )
            return 0

        # Ensure post inserter is initialized if Supabase is available
        if db_agent._supabase and not db_agent._post_inserter:
            try:
                from src.services.supabase.post_inserter import PostInserter
                from src.shared.utils.duplicate_detector import DuplicateDetector

                duplicate_checker = None
                if db_agent._dupes:

                    class _DuplicateCheckerWrapper:
                        def __init__(self, detector):
                            self.detector = detector

                        def check_duplicate_post(
                            self, content, author, platform, url=None
                        ):
                            item = {
                                "content": content,
                                "author": author,
                                "platform": platform,
                                "url": url,
                            }
                            return self.detector.is_duplicate(item)

                    duplicate_checker = _DuplicateCheckerWrapper(db_agent._dupes)
                db_agent._post_inserter = PostInserter(
                    db_agent._supabase, duplicate_checker
                )
                logger.info("✅ Initialized post inserter for Supabase sync")
            except Exception as e:
                logger.error(f"Failed to initialize post inserter: {e}")
                return 0

        # Get all posts from SQLite that need fixing
        db_path = project_root / "beyondlines.db"
        if not db_path.exists():
            logger.error("SQLite database not found")
            return 0

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = """
            SELECT * FROM posts
            WHERE ai_summary IS NOT NULL AND ai_summary != ''
        """
        if limit:
            query += f" LIMIT {limit}"
        else:
            query += " LIMIT 500"

        cur.execute(query)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            logger.info("✅ No posts found to sync to Supabase")
            return 0

        logger.info(f"📝 Found {len(rows)} posts to sync to Supabase")

        updated_count = 0
        error_count = 0

        for idx, row in enumerate(rows, 1):
            post_data = dict(row)

            # Convert JSON strings to Python objects
            for field in [
                "tags",
                "key_concepts",
                "rewrite_reasons",
                "rewrite_risks",
                "best_persona_reasons",
                "persona_fit_scores",
                "persona_fit_reasons",
                "hashtags",
                "mentions",
                "time_sensitive_reasons",
            ]:
                if post_data.get(field) and isinstance(post_data[field], str):
                    try:
                        post_data[field] = json.loads(post_data[field])
                    except:
                        pass

            # Use DatabaseAgent's normalization (same as live system)
            post_data, updated = fix_post_data(post_data, db_agent)

            # Use post inserter directly to avoid duplicate checking (faster for backfill)
            # This bypasses the duplicate check in save_post() which is slow for bulk operations
            try:
                if db_agent._post_inserter:
                    result = db_agent._post_inserter.insert_post(post_data)
                    if result:
                        updated_count += 1
                    else:
                        error_count += 1
                else:
                    logger.error("Post inserter not available")
                    break

                # Progress reporting every 10 posts
                if idx % 10 == 0:
                    logger.info(
                        f"   Progress: {idx}/{len(rows)} posts processed ({updated_count} successful, {error_count} errors)"
                    )
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Failed to update Supabase post {post_data.get('post_id')}: {e}"
                )
                # Continue processing other posts even if one fails

        logger.info(
            f"✅ Fixed {updated_count} posts in Supabase ({error_count} errors, {len(rows) - updated_count - error_count} skipped)"
        )
        return updated_count

    except Exception as e:
        logger.error(f"Supabase fix failed: {e}")
        return 0


def main():
    """Main fix function"""
    import argparse

    parser = argparse.ArgumentParser(description="Fix all corrupted data")
    parser.add_argument("--limit", type=int, help="Limit number of posts to process")
    parser.add_argument(
        "--supabase-only", action="store_true", help="Only update Supabase"
    )
    parser.add_argument("--sqlite-only", action="store_true", help="Only update SQLite")

    args = parser.parse_args()

    logger.info("🚀 Starting comprehensive data quality fix...")

    sqlite_count = 0
    supabase_count = 0

    if not args.supabase_only:
        sqlite_count = fix_sqlite_database(limit=args.limit)

    if not args.sqlite_only:
        supabase_count = fix_supabase_database(limit=args.limit)

    logger.info(f"✅ Fix complete: {sqlite_count} SQLite, {supabase_count} Supabase")

    return 0


if __name__ == "__main__":
    sys.exit(main())
