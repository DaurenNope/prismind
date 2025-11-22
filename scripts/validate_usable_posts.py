"""
Validate usable_posts table data quality.
Checks that all posts meet the strict curation criteria.
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.curate_usable_posts import (
    check_content_quality,
    check_time_sensitive_keywords,
    parse_datetime,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def validate_usable_posts(db_path: str = "beyondlines.db") -> Dict[str, Any]:
    """Validate that usable posts meet all criteria"""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all posts that would be marked as usable
    cur.execute(
        """
        SELECT
            post_id, platform, created_at, relevance_window, urgency_score,
            time_sensitive, category, ai_summary, rewrite_score, value_score, quality_score,
            analysis_model, content, title
        FROM posts
        WHERE ai_summary IS NOT NULL
        AND ai_summary != ''
        AND analysis_model IN ('gemini', 'mistral', 'ollama', 'qwen', 'qwen2.5:1.5b', 'qwen2.5:7b')
        AND rewrite_score > 0
        AND value_score > 0
        AND quality_score > 0
        AND category != 'DEPRECATED'
        ORDER BY created_at DESC
    """
    )

    all_posts = cur.fetchall()
    now = datetime.now(timezone.utc)

    validation_results = {
        "total_analyzed": len(all_posts),
        "passing_all_checks": 0,
        "failing_content_quality": 0,
        "failing_time_sensitive_keywords": 0,
        "failing_age_requirements": 0,
        "failing_other": 0,
        "issues": [],
    }

    for row in all_posts:
        post = dict(row)

        # Check content quality
        content_valid, content_error = check_content_quality(post)
        if not content_valid:
            validation_results["failing_content_quality"] += 1
            validation_results["issues"].append(
                {
                    "post_id": post["post_id"],
                    "platform": post["platform"],
                    "issue": "content_quality",
                    "error": content_error,
                }
            )
            continue

        # Check if evergreen or fresh time-sensitive
        relevance_window = post.get("relevance_window", "evergreen")
        urgency_score = post.get("urgency_score") or 0.0
        time_sensitive = post.get("time_sensitive", False)
        category = post.get("category", "").upper()
        created_at = post.get("created_at")

        # Parse age
        age_info = None
        if created_at:
            try:
                created_dt = parse_datetime(created_at)
                if created_dt:
                    if created_dt.tzinfo:
                        now_dt = now if now.tzinfo else datetime.now(created_dt.tzinfo)
                    else:
                        now_dt = datetime.now(timezone.utc)
                        created_dt = created_dt.replace(tzinfo=timezone.utc)

                    age_days = (now_dt - created_dt).days
                    age_months = age_days / 30.0

                    age_info = {"days": age_days, "months": age_months}
            except Exception:
                pass

        is_usable = False
        reason = None

        # Check evergreen posts
        if relevance_window == "evergreen":
            # Must not be false evergreen
            if urgency_score >= 0.35 or time_sensitive or category == "NEWS":
                validation_results["failing_other"] += 1
                continue

            # Check for time-sensitive keywords
            content = post.get("content", "") or ""
            ai_summary = post.get("ai_summary", "") or ""
            if check_time_sensitive_keywords(content, ai_summary):
                validation_results["failing_time_sensitive_keywords"] += 1
                validation_results["issues"].append(
                    {
                        "post_id": post["post_id"],
                        "platform": post["platform"],
                        "issue": "time_sensitive_keywords",
                        "error": "Contains time-sensitive keywords in evergreen content",
                    }
                )
                continue

            # Check age
            if age_info:
                if age_info["months"] >= 6.0:
                    validation_results["failing_age_requirements"] += 1
                    continue
                if age_info["days"] < 7:
                    validation_results["failing_age_requirements"] += 1
                    continue
                is_usable = True
                reason = "truly_evergreen"
            else:
                validation_results["failing_other"] += 1
                continue

        # Check fresh time-sensitive posts
        elif relevance_window in ("same-day", "24-72h", "this-week"):
            if age_info:
                if age_info["days"] <= 7:
                    is_usable = True
                    reason = "fresh_time_sensitive"
                else:
                    validation_results["failing_age_requirements"] += 1
                    continue
            else:
                validation_results["failing_other"] += 1
                continue

        # Other relevance windows
        else:
            validation_results["failing_other"] += 1
            continue

        if is_usable:
            validation_results["passing_all_checks"] += 1

    conn.close()
    return validation_results


def main():
    """Main validation function"""
    print("=" * 80)
    print("🔍 VALIDATING USABLE POSTS")
    print("=" * 80)

    results = validate_usable_posts()

    print(f"\n📊 VALIDATION RESULTS:")
    print(f"   Total analyzed: {results['total_analyzed']}")
    print(
        f"   ✅ Passing all checks: {results['passing_all_checks']} ({results['passing_all_checks']/results['total_analyzed']*100:.1f}%)"
    )
    print(f"   ❌ Failing content quality: {results['failing_content_quality']}")
    print(
        f"   ❌ Failing time-sensitive keywords: {results['failing_time_sensitive_keywords']}"
    )
    print(f"   ❌ Failing age requirements: {results['failing_age_requirements']}")
    print(f"   ❌ Failing other: {results['failing_other']}")

    # Show sample issues
    if results["issues"]:
        print(f"\n📋 SAMPLE ISSUES (first 10):")
        for issue in results["issues"][:10]:
            print(
                f"   {issue['post_id']} ({issue['platform']}): {issue['issue']} - {issue['error']}"
            )

    # Verify against curation script
    print(f"\n🔍 VERIFYING AGAINST CURATION SCRIPT...")
    from scripts.curate_usable_posts import get_usable_posts_from_sqlite

    usable_posts, excluded_posts = get_usable_posts_from_sqlite()

    print(f"   Curation script found: {len(usable_posts)} usable posts")
    print(f"   Validation found: {results['passing_all_checks']} usable posts")

    if len(usable_posts) == results["passing_all_checks"]:
        print(f"   ✅ MATCH! Validation confirms curation script results")
    else:
        print(
            f"   ⚠️  MISMATCH! Difference: {abs(len(usable_posts) - results['passing_all_checks'])}"
        )

    print(f"\n{'='*80}")

    return results


if __name__ == "__main__":
    main()




