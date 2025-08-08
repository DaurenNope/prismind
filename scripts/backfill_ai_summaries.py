#!/usr/bin/env python3
"""
Backfill AI summaries, key concepts, and sentiment for posts missing them.

Usage:
  # Local-only backfill
  OLLAMA_URL=http://localhost:11434 OLLAMA_MODEL=qwen2.5:7b \
  python scripts/backfill_ai_summaries.py

  # Also update Supabase when env vars are set
  SAVE_TO_SUPABASE=1 SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  OLLAMA_URL=http://localhost:11434 OLLAMA_MODEL=qwen2.5:7b \
  python scripts/backfill_ai_summaries.py
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict

from core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
from supabase_manager import SupabaseManager

DB_PATH = os.getenv("PRISMIND_DB", "data/prismind.db")


def rows_missing_summary(conn: sqlite3.Connection) -> list[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM posts
        WHERE is_deleted = 0 AND (ai_summary IS NULL OR TRIM(ai_summary) = '')
        ORDER BY created_timestamp DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def backfill_one(analyzer: IntelligentContentAnalyzer, row: Dict[str, Any]) -> Dict[str, Any]:
    # Build a minimal SocialPost-like dict for analysis
    from core.extraction.social_extractor_base import SocialPost

    created_at = row.get("created_at")
    try:
        if isinstance(created_at, str) and created_at:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except Exception:
        created_at = datetime.utcnow()

    post = SocialPost(
        platform=row.get("platform", "twitter"),
        post_id=row.get("post_id", ""),
        author=row.get("author", ""),
        author_handle=row.get("author_handle", row.get("author", "")),
        content=row.get("content", ""),
        created_at=created_at,
        url=row.get("url", ""),
        post_type=row.get("post_type", "post"),
        media_urls=[],
        hashtags=[],
        mentions=[],
        engagement={},
        is_saved=True,
        saved_at=None,
        folder_category=row.get("folder_category", ""),
        analysis=None,
    )

    analysis = analyzer.analyze_bookmark(post, include_comments=False, include_media=False)
    return {
        "category": analysis.get("category"),
        "ai_summary": analysis.get("summary", ""),
        "sentiment": analysis.get("sentiment"),
        "key_concepts": str(analysis.get("key_concepts", [])),
        "value_score": analysis.get("intelligent_value_score", analysis.get("value_score")),
    }


def main():
    print(f"🔧 Backfilling AI summaries in {DB_PATH}…")
    analyzer = IntelligentContentAnalyzer()
    sync_supabase = os.getenv("SAVE_TO_SUPABASE", "0") == "1"
    supa = None
    if sync_supabase:
        try:
            supa = SupabaseManager()
            print("✅ Supabase sync enabled")
        except Exception as e:
            print(f"⚠️ Supabase disabled: {e}")
            supa = None
    updated = 0
    with sqlite3.connect(DB_PATH) as conn:
        posts = rows_missing_summary(conn)
        print(f"Found {len(posts)} posts missing ai_summary")
        for row in posts:
            try:
                updates = backfill_one(analyzer, row)
                conn.execute(
                    """
                    UPDATE posts
                    SET category = COALESCE(?, category),
                        ai_summary = ?,
                        sentiment = COALESCE(?, sentiment),
                        key_concepts = COALESCE(?, key_concepts),
                        value_score = COALESCE(?, value_score)
                    WHERE post_id = ?
                    """,
                    (
                        updates.get("category"),
                        updates.get("ai_summary", ""),
                        updates.get("sentiment"),
                        updates.get("key_concepts"),
                        updates.get("value_score"),
                        row["post_id"],
                    ),
                )
                conn.commit()
                updated += 1
                print(f"✅ Backfilled {row['post_id']}")
                # Optional: sync to Supabase
                if supa is not None:
                    supa.update_post(row.get('id'), {
                        'category': updates.get('category'),
                        'ai_summary': updates.get('ai_summary', ''),
                        'sentiment': updates.get('sentiment'),
                        'key_concepts': updates.get('key_concepts'),
                        'value_score': updates.get('value_score'),
                    })
            except Exception as e:
                print(f"⚠️ Failed {row.get('post_id')}: {e}")
                continue
    print(f"🎉 Done. Updated {updated} posts.")


if __name__ == "__main__":
    main()


