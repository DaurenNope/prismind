#!/usr/bin/env python3
"""
Re-analyze posts with missing or incorrect analysis data using Qwen 1.5B via Ollama
This ensures all posts have proper values for rewriter and discovery
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Force Ollama/Qwen 1.5B for re-analysis - disable other services
os.environ["ANALYZER_PRIMARY"] = "ollama"
os.environ["OLLAMA_MODEL"] = "qwen2.5:1.5b"
os.environ["OLLAMA_URL"] = os.getenv("OLLAMA_URL", "http://localhost:11434")
# Disable Gemini and Mistral to force Ollama usage
os.environ["GEMINI_API_KEY"] = ""  # Empty key disables Gemini
os.environ["MISTRAL_API_KEY"] = ""  # Empty key disables Mistral

import sqlite3

from src.infrastructure.database.database_agent import DatabaseAgent
from src.domain.analysis.services.post_analyzer import analyze_and_store_post
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


async def reanalyze_posts(limit=None, force=False):
    """
    Re-analyze posts with missing or incorrect analysis data

    Args:
        limit: Limit number of posts to re-analyze
        force: Force re-analysis even if analysis exists
    """
    db_agent = DatabaseAgent()

    # Get posts that need re-analysis
    db_path = project_root / "beyondlines.db"
    if not db_path.exists():
        logger.error("SQLite database not found")
        return 0

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Find posts that need re-analysis
    if force:
        # Re-analyze all posts
        query = """
            SELECT * FROM posts
            WHERE ai_summary IS NOT NULL AND ai_summary != ''
            ORDER BY created_at DESC
        """
    else:
        # Only re-analyze posts with missing/incorrect analysis data
        query = """
            SELECT * FROM posts
            WHERE (
                -- Missing or corrupted analysis_model
                analysis_model IS NULL OR
                analysis_model = '' OR
                analysis_model NOT IN ('gemini', 'mistral', 'ollama', 'qwen', 'qwen2.5:1.5b', 'qwen2.5:7b') OR
                -- Missing critical fields
                category IS NULL OR category = '' OR category = 'unknown' OR
                best_persona_key IS NULL OR
                rewrite_score IS NULL OR rewrite_score = 0.0 OR
                value_score IS NULL OR value_score = 0.0 OR
                quality_score IS NULL OR quality_score = 0.0 OR
                -- Incorrect relevance_window (evergreen when urgency_score > 0.35)
                (relevance_window = 'evergreen' AND urgency_score > 0.35) OR
                -- Missing rewrite_readiness
                rewrite_readiness IS NULL OR rewrite_readiness = '' OR
                -- Missing rewrite_reasons
                rewrite_reasons IS NULL OR rewrite_reasons = '[]' OR rewrite_reasons = ''
            )
            AND ai_summary IS NOT NULL AND ai_summary != ''
            ORDER BY created_at DESC
        """

    if limit:
        query += f" LIMIT {limit}"
    else:
        query += " LIMIT 100"  # Default limit

    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        logger.info("✅ No posts need re-analysis")
        return 0

    logger.info(f"📝 Found {len(rows)} posts to re-analyze")

    reanalyzed_count = 0
    error_count = 0

    for idx, row in enumerate(rows, 1):
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
            "time_sensitive_reasons",
        ]:
            if post_data.get(field) and isinstance(post_data[field], str):
                try:
                    post_data[field] = json.loads(post_data[field])
                except:
                    pass

        try:
            # Re-analyze the post
            logger.info(
                f"Re-analyzing post {post_data.get('post_id')} ({idx}/{len(rows)})..."
            )
            result = await analyze_and_store_post(db_agent, post_data)

            if result:
                reanalyzed_count += 1
                if reanalyzed_count % 10 == 0:
                    logger.info(
                        f"   Progress: {reanalyzed_count}/{len(rows)} posts re-analyzed"
                    )
            else:
                error_count += 1
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to re-analyze post {post_data.get('post_id')}: {e}")
            # Continue processing other posts even if one fails

    logger.info(f"✅ Re-analyzed {reanalyzed_count} posts ({error_count} errors)")
    return reanalyzed_count


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Re-analyze posts with missing or incorrect analysis data"
    )
    parser.add_argument("--limit", type=int, help="Limit number of posts to re-analyze")
    parser.add_argument(
        "--force", action="store_true", help="Force re-analysis of all posts"
    )

    args = parser.parse_args()

    logger.info("🚀 Starting post re-analysis...")

    count = await reanalyze_posts(limit=args.limit, force=args.force)

    logger.info(f"✅ Re-analysis complete: {count} posts re-analyzed")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
