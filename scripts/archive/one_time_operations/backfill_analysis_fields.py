#!/usr/bin/env python3
"""
Backfill missing analysis fields for existing posts
Applies the same default logic as the analyzer to ensure all posts have complete data
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from datetime import datetime

from src.infrastructure.database.database_agent import DatabaseAgent
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def _to_score(x):
    """Normalize score to float in 0-10 range"""
    try:
        v = float(x)
    except Exception:
        v = 0.0
    return max(0.0, min(10.0, v))


def backfill_post_fields(post_data: dict) -> dict:
    """Apply defaults to missing analysis fields"""
    updated = False

    # Rewrite-focused defaults
    if post_data.get("rewrite_score") is None:
        # Use value_score as base for rewrite_score
        vs = _to_score(post_data.get("value_score", 0.0))
        post_data["rewrite_score"] = vs
        updated = True

    if not post_data.get("rewrite_readiness"):
        summary = post_data.get("ai_summary") or ""
        summary_len = len(summary)
        post_data["rewrite_readiness"] = (
            "ready"
            if summary_len >= 150
            else ("needs_context" if summary_len < 80 else "needs_trim")
        )
        updated = True

    if post_data.get("rewrite_reasons") is None:
        tags = post_data.get("tags") or []
        concepts = post_data.get("key_concepts") or []
        tags_count = len(tags) if isinstance(tags, list) else 0
        concepts_count = len(concepts) if isinstance(concepts, list) else 0
        post_data["rewrite_reasons"] = [
            f"Good tags ({tags_count})",
            f"Concepts ({concepts_count})",
        ]
        updated = True

    if post_data.get("rewrite_risks") is None:
        risks = []
        summary = post_data.get("ai_summary") or ""
        if len(summary) < 120:
            risks.append("Short summary")
        tags = post_data.get("tags") or []
        if not tags or (isinstance(tags, list) and len(tags) == 0):
            risks.append("No tags")
        post_data["rewrite_risks"] = risks
        updated = True

    if post_data.get("analysis_confidence") is None:
        post_data["analysis_confidence"] = 0.7
        updated = True

    if not post_data.get("analysis_depth"):
        post_data["analysis_depth"] = "fast"
        updated = True

    if post_data.get("needs_deep_analysis") is None:
        rewrite_score = _to_score(post_data.get("rewrite_score", 0.0))
        confidence = post_data.get("analysis_confidence", 0.7)
        post_data["needs_deep_analysis"] = (
            True if rewrite_score >= 8 and confidence < 0.8 else False
        )
        updated = True

    # Persona fit defaults
    if post_data.get("persona_fit_scores") is None:
        post_data["persona_fit_scores"] = {}
        updated = True

    if post_data.get("persona_fit_reasons") is None:
        post_data["persona_fit_reasons"] = {}
        updated = True

    # Fix corrupted best_persona_key values (should be persona name, not "evergreen" or other time sensitivity values)
    best_key = post_data.get("best_persona_key")
    invalid_values = ["evergreen", "timely", "trending", "breaking", "urgent"]
    if best_key in invalid_values:
        post_data["best_persona_key"] = None
        updated = True
    elif not best_key:
        post_data["best_persona_key"] = None
        updated = True

    if post_data.get("best_persona_score") is None:
        post_data["best_persona_score"] = 0.0
        updated = True

    if post_data.get("best_persona_reasons") is None:
        post_data["best_persona_reasons"] = []
        updated = True

    # Normalize numeric fields
    if isinstance(post_data.get("rewrite_score"), str):
        post_data["rewrite_score"] = _to_score(post_data["rewrite_score"])
        updated = True

    if isinstance(post_data.get("analysis_confidence"), str):
        try:
            post_data["analysis_confidence"] = float(post_data["analysis_confidence"])
        except:
            post_data["analysis_confidence"] = 0.7
        updated = True

    if isinstance(post_data.get("best_persona_score"), str):
        post_data["best_persona_score"] = _to_score(post_data["best_persona_score"])
        updated = True

    if isinstance(post_data.get("quality_score"), str):
        post_data["quality_score"] = _to_score(post_data["quality_score"])
        updated = True

    if isinstance(post_data.get("value_score"), str):
        post_data["value_score"] = _to_score(post_data["value_score"])
        updated = True

    return post_data, updated


def backfill_sqlite_posts(limit=None):
    """Backfill missing fields in SQLite database"""
    db_path = project_root / "beyondlines.db"
    if not db_path.exists():
        logger.error("SQLite database not found")
        return 0

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Find posts missing important fields or with corrupted values
    query = """
        SELECT * FROM posts
        WHERE
            rewrite_score IS NULL OR
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
            best_persona_key IN ('evergreen', 'timely', 'trending', 'breaking', 'urgent')
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    rows = cur.fetchall()

    if not rows:
        logger.info("✅ No posts need backfilling in SQLite")
        conn.close()
        return 0

    logger.info(f"📝 Found {len(rows)} posts needing backfill in SQLite")

    updated_count = 0
    for row in rows:
        post_data = dict(row)

        # Convert JSON strings to Python objects
        import json

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
        ]:
            if post_data.get(field) and isinstance(post_data[field], str):
                try:
                    post_data[field] = json.loads(post_data[field])
                except:
                    pass

        post_data, updated = backfill_post_fields(post_data)

        if updated:
            # Update SQLite
            try:
                cur.execute(
                    """
                    UPDATE posts SET
                        rewrite_score = ?,
                        rewrite_readiness = ?,
                        rewrite_reasons = ?,
                        rewrite_risks = ?,
                        analysis_confidence = ?,
                        analysis_depth = ?,
                        needs_deep_analysis = ?,
                        persona_fit_scores = ?,
                        persona_fit_reasons = ?,
                        best_persona_key = ?,
                        best_persona_score = ?,
                        best_persona_reasons = ?,
                        value_score = ?,
                        quality_score = ?
                    WHERE post_id = ?
                """,
                    (
                        post_data.get("rewrite_score"),
                        post_data.get("rewrite_readiness"),
                        json.dumps(post_data.get("rewrite_reasons", [])),
                        json.dumps(post_data.get("rewrite_risks", [])),
                        post_data.get("analysis_confidence"),
                        post_data.get("analysis_depth"),
                        1 if post_data.get("needs_deep_analysis") else 0,
                        json.dumps(post_data.get("persona_fit_scores", {})),
                        json.dumps(post_data.get("persona_fit_reasons", {})),
                        post_data.get("best_persona_key"),
                        post_data.get("best_persona_score"),
                        json.dumps(post_data.get("best_persona_reasons", [])),
                        post_data.get("value_score"),
                        post_data.get("quality_score"),
                        post_data.get("post_id"),
                    ),
                )
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update post {post_data.get('post_id')}: {e}")

    conn.commit()
    conn.close()

    logger.info(f"✅ Updated {updated_count} posts in SQLite")
    return updated_count


def backfill_supabase_posts(limit=None):
    """Backfill missing fields in Supabase"""
    try:
        db_agent = DatabaseAgent()
        if not db_agent._post_inserter:
            logger.warning("Post inserter not available, skipping Supabase backfill")
            return 0

        # Get post inserter
        post_inserter = db_agent._post_inserter

        # Get all posts from SQLite that have been analyzed (have ai_summary)
        db_path = project_root / "beyondlines.db"
        if not db_path.exists():
            logger.error("SQLite database not found")
            return 0

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Get all posts that have been analyzed (have ai_summary) to sync to Supabase
        query = """
            SELECT * FROM posts
            WHERE ai_summary IS NOT NULL AND ai_summary != ''
        """
        if limit:
            query += f" LIMIT {limit}"
        else:
            query += " LIMIT 500"  # Default limit to avoid overwhelming Supabase

        cur.execute(query)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            logger.info("✅ No analyzed posts found to sync to Supabase")
            return 0

        logger.info(f"📝 Found {len(rows)} analyzed posts to sync to Supabase")

        updated_count = 0
        import json

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
            ]:
                if post_data.get(field) and isinstance(post_data[field], str):
                    try:
                        post_data[field] = json.loads(post_data[field])
                    except:
                        pass

            # Always backfill fields (even if already filled, ensures consistency)
            post_data, updated = backfill_post_fields(post_data)

            try:
                # Use post inserter to upsert to Supabase (will update existing posts)
                result = post_inserter.insert_post(post_data)
                if result:
                    updated_count += 1
                    if updated_count % 50 == 0:
                        logger.info(
                            f"   Synced {updated_count}/{len(rows)} posts to Supabase..."
                        )
            except Exception as e:
                logger.error(
                    f"Failed to update Supabase post {post_data.get('post_id')}: {e}"
                )

        logger.info(f"✅ Updated {updated_count} posts in Supabase")
        return updated_count

    except Exception as e:
        logger.error(f"Supabase backfill failed: {e}")
        return 0


def main():
    """Main backfill function"""
    import argparse

    parser = argparse.ArgumentParser(description="Backfill missing analysis fields")
    parser.add_argument("--limit", type=int, help="Limit number of posts to process")
    parser.add_argument(
        "--supabase-only", action="store_true", help="Only update Supabase"
    )
    parser.add_argument("--sqlite-only", action="store_true", help="Only update SQLite")

    args = parser.parse_args()

    logger.info("🚀 Starting analysis fields backfill...")

    sqlite_count = 0
    supabase_count = 0

    if not args.supabase_only:
        sqlite_count = backfill_sqlite_posts(limit=args.limit)

    if not args.sqlite_only:
        supabase_count = backfill_supabase_posts(limit=args.limit)

    logger.info(
        f"✅ Backfill complete: {sqlite_count} SQLite, {supabase_count} Supabase"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
