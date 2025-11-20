"""
Comprehensive validation to ensure 100% usable content.
Checks for all potential edge cases and issues.
"""

import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.curate_usable_posts import (
    check_content_quality,
    check_time_sensitive_keywords,
    get_usable_posts_from_sqlite,
    is_post_usable,
    parse_datetime,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def check_all_edge_cases(post: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Check for all potential edge cases and issues.

    Returns:
        List of (issue_type, description) tuples
    """
    issues = []

    # 1. Content quality checks
    content_valid, content_error = check_content_quality(post)
    if not content_valid:
        issues.append(("content_quality", content_error))

    # 2. Time-sensitive keyword detection (for evergreen posts)
    if post.get("relevance_window") == "evergreen":
        content = post.get("content", "") or ""
        ai_summary = post.get("ai_summary", "") or ""
        if check_time_sensitive_keywords(content, ai_summary):
            issues.append(
                (
                    "time_sensitive_keywords",
                    "Contains time-sensitive keywords in evergreen content",
                )
            )

    # 3. Age validation edge cases
    created_at = post.get("created_at")
    if created_at:
        try:
            created_dt = parse_datetime(created_at)
            if created_dt:
                now = datetime.now(timezone.utc)
                if created_dt.tzinfo:
                    now_dt = now if now.tzinfo else datetime.now(created_dt.tzinfo)
                else:
                    now_dt = datetime.now(timezone.utc)
                    created_dt = created_dt.replace(tzinfo=timezone.utc)

                age_days = (now_dt - created_dt).days
                age_months = age_days / 30.0

                # Edge case: Exactly 7 days old (boundary condition)
                if age_days == 7 and post.get("relevance_window") == "evergreen":
                    # This is OK - it's exactly at the minimum threshold
                    pass
                elif age_days < 7 and post.get("relevance_window") == "evergreen":
                    issues.append(
                        (
                            "age_validation",
                            f"Evergreen post is too recent ({age_days} days old, need >=7 days)",
                        )
                    )

                # Edge case: Exactly 6 months old (boundary condition)
                if age_months >= 6.0 and post.get("relevance_window") == "evergreen":
                    issues.append(
                        (
                            "age_validation",
                            f"Evergreen post is too old ({age_months:.1f} months, need <6 months)",
                        )
                    )

                # Edge case: Time-sensitive post >7 days old
                if post.get("relevance_window") in ("same-day", "24-72h", "this-week"):
                    if age_days > 7:
                        issues.append(
                            (
                                "age_validation",
                                f"Time-sensitive post is too old ({age_days} days, need <=7 days)",
                            )
                        )
        except Exception as e:
            issues.append(("age_validation", f"Could not parse created_at: {e}"))

    # 4. Score validation edge cases
    rewrite_score = post.get("rewrite_score", 0) or 0
    value_score = post.get("value_score", 0) or 0
    quality_score = post.get("quality_score", 0) or 0

    if rewrite_score <= 0:
        issues.append(
            ("score_validation", f"rewrite_score is {rewrite_score} (must be > 0)")
        )
    if value_score <= 0:
        issues.append(
            ("score_validation", f"value_score is {value_score} (must be > 0)")
        )
    if quality_score <= 0:
        issues.append(
            ("score_validation", f"quality_score is {quality_score} (must be > 0)")
        )

    # 5. Category validation
    category = (post.get("category") or "").upper()
    if category == "DEPRECATED":
        issues.append(("category_validation", "Category is DEPRECATED"))
    if category == "NEWS" and post.get("relevance_window") == "evergreen":
        issues.append(("category_validation", "NEWS category cannot be evergreen"))

    # 6. Analysis model validation
    analysis_model = post.get("analysis_model")
    valid_models = ["gemini", "mistral", "ollama", "qwen", "qwen2.5:1.5b", "qwen2.5:7b"]
    if not analysis_model or analysis_model not in valid_models:
        issues.append(("analysis_model", f"Invalid analysis_model: {analysis_model}"))

    # 7. AI summary validation
    ai_summary = post.get("ai_summary", "") or ""
    if not ai_summary or len(ai_summary.strip()) < 50:
        issues.append(("ai_summary", "AI summary is missing or too short"))

    # 8. Urgency score validation (for evergreen)
    if post.get("relevance_window") == "evergreen":
        urgency_score = post.get("urgency_score") or 0.0
        if urgency_score >= 0.35:
            issues.append(
                (
                    "urgency_validation",
                    f"Evergreen post has high urgency ({urgency_score:.2f} >= 0.35)",
                )
            )

    # 9. Time-sensitive flag validation (for evergreen)
    if post.get("relevance_window") == "evergreen":
        if post.get("time_sensitive", False):
            issues.append(
                ("time_sensitive_flag", "Evergreen post is marked as time_sensitive")
            )

    # 10. Required fields validation
    required_fields = [
        "post_id",
        "platform",
        "content",
        "ai_summary",
        "rewrite_score",
        "value_score",
        "quality_score",
        "category",
        "relevance_window",
    ]
    for field in required_fields:
        if not post.get(field):
            issues.append(("required_fields", f"Missing required field: {field}"))

    # 11. Content length validation
    content = post.get("content", "") or ""
    if len(content) < 50:
        issues.append(
            (
                "content_length",
                f"Content is too short ({len(content)} chars, need >=50)",
            )
        )

    # 12. Check for suspicious patterns in content
    content_lower = content.lower()
    suspicious_patterns = [
        (
            r"\b(test|testing|example|sample|placeholder)\b",
            "Contains test/placeholder language",
        ),
        (r"\[deleted\]|\[removed\]", "Content is deleted/removed"),
        (r"error|failed|exception", "Contains error language"),
    ]

    for pattern, description in suspicious_patterns:
        if re.search(pattern, content_lower):
            # Only flag if it's clearly problematic (not just mentioning the word)
            if pattern == r"\[deleted\]|\[removed\]":
                issues.append(("suspicious_content", description))
            elif pattern == r"error|failed|exception" and len(content) < 200:
                # Short content with error words is suspicious
                issues.append(("suspicious_content", description))

    # 13. Check for truncated content (additional checks)
    content_stripped = content.strip()
    if content_stripped.endswith("...") or content_stripped.endswith("…"):
        issues.append(("truncation", "Content ends with truncation markers"))

    # 14. Check for placeholder AI summaries
    ai_summary_lower = ai_summary.lower()
    if "placeholder" in ai_summary_lower or "error" in ai_summary_lower[:100]:
        issues.append(
            ("ai_summary_quality", "AI summary appears to be placeholder or error")
        )

    return issues


def comprehensive_validation(db_path: str = "beyondlines.db") -> Dict[str, Any]:
    """Run comprehensive validation on all usable posts"""

    # Get usable posts
    usable_posts, excluded_posts = get_usable_posts_from_sqlite(db_path)

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    results = {
        "total_usable_posts": len(usable_posts),
        "posts_with_issues": 0,
        "total_issues": 0,
        "issues_by_type": {},
        "posts_with_issues_list": [],
    }

    # Check all usable posts
    for post in usable_posts:
        post_id = post.get("post_id")
        platform = post.get("platform")

        # Re-fetch from DB to get full data
        cur.execute(
            "SELECT * FROM posts WHERE post_id = ? AND platform = ?",
            (post_id, platform),
        )
        db_post = cur.fetchone()
        if not db_post:
            results["posts_with_issues"] += 1
            results["total_issues"] += 1
            results["issues_by_type"]["not_found"] = (
                results["issues_by_type"].get("not_found", 0) + 1
            )
            results["posts_with_issues_list"].append(
                {
                    "post_id": post_id,
                    "platform": platform,
                    "issues": [("not_found", "Post not found in database")],
                }
            )
            continue

        db_post_dict = dict(db_post)

        # Check all edge cases
        issues = check_all_edge_cases(db_post_dict)

        if issues:
            results["posts_with_issues"] += 1
            results["total_issues"] += len(issues)

            for issue_type, description in issues:
                results["issues_by_type"][issue_type] = (
                    results["issues_by_type"].get(issue_type, 0) + 1
                )

            results["posts_with_issues_list"].append(
                {"post_id": post_id, "platform": platform, "issues": issues}
            )

    conn.close()
    return results


def main():
    """Main validation function"""
    print("=" * 80)
    print("🔍 COMPREHENSIVE VALIDATION: Ensuring 100% Usable Content")
    print("=" * 80)

    results = comprehensive_validation()

    print(f"\n📊 VALIDATION RESULTS:")
    print(f"   Total usable posts: {results['total_usable_posts']}")
    print(f"   Posts with issues: {results['posts_with_issues']}")
    print(f"   Total issues found: {results['total_issues']}")

    if results["posts_with_issues"] == 0:
        print(
            f"\n✅ PERFECT! All {results['total_usable_posts']} posts pass all validation checks!"
        )
        print(f"   🎉 100% confidence: All content is usable!")
    else:
        print(f"\n❌ FOUND ISSUES:")
        print(
            f"   {results['posts_with_issues']} posts have issues ({results['posts_with_issues']/results['total_usable_posts']*100:.1f}%)"
        )

        print(f"\n   Issues by type:")
        for issue_type, count in sorted(
            results["issues_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"     - {issue_type}: {count}")

        print(f"\n   Sample posts with issues (first 10):")
        for post_info in results["posts_with_issues_list"][:10]:
            print(f"     - {post_info['post_id']} ({post_info['platform']}):")
            for issue_type, description in post_info["issues"]:
                print(f"       • {issue_type}: {description}")

    print(f"\n{'='*80}")

    return results


if __name__ == "__main__":
    results = main()
    sys.exit(0 if results["posts_with_issues"] == 0 else 1)

