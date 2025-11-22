"""
Validate evergreen posts and identify truly usable content.
This script checks if posts marked as "evergreen" are actually time-sensitive,
and identifies which posts should be in the usable_posts table.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def parse_datetime(date_str):
    """Parse datetime from various formats"""
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str

    try:
        # Try ISO format
        if "T" in str(date_str):
            return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        # Try other formats
        return datetime.strptime(str(date_str)[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def analyze_evergreen_accuracy():
    """Analyze if evergreen posts are truly evergreen"""
    conn = sqlite3.connect("beyondlines.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=" * 80)
    print("🔍 VALIDATING EVERGREEN POSTS")
    print("=" * 80)

    # Get all posts with analysis
    cur.execute(
        """
        SELECT
            post_id, platform, created_at, relevance_window, urgency_score,
            time_sensitive, category, ai_summary, rewrite_score, value_score, quality_score
        FROM posts
        WHERE ai_summary IS NOT NULL
        AND ai_summary != ''
        AND analysis_model IN ('gemini', 'mistral', 'ollama', 'qwen', 'qwen2.5:1.5b', 'qwen2.5:7b')
        ORDER BY created_at DESC
    """
    )

    posts = cur.fetchall()
    total = len(posts)
    print(f"\n📊 Total analyzed posts: {total}\n")

    # Analyze evergreen posts
    evergreen_posts = []
    false_evergreen = []  # Posts marked evergreen but actually time-sensitive
    true_evergreen = []  # Posts that are truly evergreen

    for row in posts:
        relevance_window = row["relevance_window"]
        urgency_score = row["urgency_score"] or 0.0
        time_sensitive = row["time_sensitive"]
        category = row["category"] or ""
        created_at = row["created_at"]

        if relevance_window == "evergreen":
            evergreen_posts.append(row)

            # Check if it's actually time-sensitive
            is_false_evergreen = False
            reasons = []

            # High urgency score (> 0.35 suggests time-sensitive)
            if urgency_score >= 0.35:
                is_false_evergreen = True
                reasons.append(f"High urgency ({urgency_score:.2f})")

            # Explicitly marked as time-sensitive
            if time_sensitive:
                is_false_evergreen = True
                reasons.append("time_sensitive flag set")

            # NEWS category (inherently time-sensitive)
            if category.upper() == "NEWS":
                is_false_evergreen = True
                reasons.append("NEWS category")

            # Calculate age
            age_info = None
            if created_at:
                try:
                    created_dt = parse_datetime(created_at)
                    if created_dt:
                        if created_dt.tzinfo:
                            now = datetime.now(created_dt.tzinfo)
                        else:
                            now = datetime.now(timezone.utc)
                            created_dt = created_dt.replace(tzinfo=timezone.utc)

                        age_days = (now - created_dt).days
                        age_months = age_days / 30.0
                        age_years = age_days / 365.0

                        age_info = {
                            "days": age_days,
                            "months": age_months,
                            "years": age_years,
                        }

                        # Old posts (> 1 year) are likely not truly evergreen
                        if age_years > 1:
                            is_false_evergreen = True
                            reasons.append(f"Old ({age_years:.1f} years)")
                        elif age_months >= 6:
                            is_false_evergreen = True
                            reasons.append(f"6+ months old ({age_months:.1f} months)")

                except Exception as e:
                    pass

            if is_false_evergreen:
                false_evergreen.append(
                    {"post": row, "reasons": reasons, "age": age_info}
                )
            else:
                true_evergreen.append({"post": row, "age": age_info})

    print(f"📈 EVERGREEN POSTS ANALYSIS:")
    print(f"   Total marked as 'evergreen': {len(evergreen_posts)}")
    print(f"   ✅ Truly evergreen: {len(true_evergreen)}")
    print(f"   ❌ False evergreen (actually time-sensitive): {len(false_evergreen)}")
    if len(evergreen_posts) > 0:
        print(
            f"   False positive rate: {len(false_evergreen)/len(evergreen_posts)*100:.1f}%"
        )

    # Show breakdown of false evergreen reasons
    if false_evergreen:
        print(f"\n❌ FALSE EVERGREEN BREAKDOWN:")
        urgency_count = sum(
            1
            for f in false_evergreen
            if any("High urgency" in str(r) for r in f["reasons"])
        )
        time_sensitive_count = sum(
            1
            for f in false_evergreen
            if any("time_sensitive flag" in str(r) for r in f["reasons"])
        )
        news_count = sum(
            1
            for f in false_evergreen
            if any("NEWS category" in str(r) for r in f["reasons"])
        )
        old_count = sum(
            1
            for f in false_evergreen
            if any("Old" in str(r) or "months old" in str(r) for r in f["reasons"])
        )

        print(f"   High urgency (≥0.35): {urgency_count}")
        print(f"   time_sensitive flag: {time_sensitive_count}")
        print(f"   NEWS category: {news_count}")
        print(f"   Old (>6 months): {old_count}")

    # Analyze time-sensitive posts from last month
    print(f"\n⏰ TIME-SENSITIVE POSTS ANALYSIS:")
    time_sensitive_posts = [
        p
        for p in posts
        if p["relevance_window"] and p["relevance_window"] != "evergreen"
    ]
    print(f"   Total time-sensitive posts: {len(time_sensitive_posts)}")

    # Check how many are from last month and are deprecated
    last_month_deprecated = []
    fresh_time_sensitive = []  # Time-sensitive posts from last 7 days

    for row in time_sensitive_posts:
        created_at = row["created_at"]
        relevance_window = row["relevance_window"]
        urgency_score = row["urgency_score"] or 0.0

        if created_at:
            try:
                created_dt = parse_datetime(created_at)
                if created_dt:
                    if created_dt.tzinfo:
                        now = datetime.now(created_dt.tzinfo)
                    else:
                        now = datetime.now(timezone.utc)
                        created_dt = created_dt.replace(tzinfo=timezone.utc)

                    age_days = (now - created_dt).days
                    age_months = age_days / 30.0

                    # Check if deprecated based on relevance_window
                    is_deprecated = False
                    if relevance_window == "same-day" and age_days > 1:
                        is_deprecated = True
                    elif relevance_window == "24-72h" and age_days > 3:
                        is_deprecated = True
                    elif relevance_window == "this-week" and age_days > 7:
                        is_deprecated = True
                    elif urgency_score > 0.7 and age_days > 7:
                        is_deprecated = True
                    elif urgency_score > 0.5 and age_days > 7:
                        is_deprecated = True

                    # From last month (30 days)
                    if 7 < age_days <= 30:
                        if is_deprecated:
                            last_month_deprecated.append(row)
                    elif age_days <= 7:
                        fresh_time_sensitive.append(row)

            except Exception as e:
                pass

    print(f"   Fresh (≤7 days): {len(fresh_time_sensitive)}")
    print(f"   Last month (8-30 days): {len(last_month_deprecated)} (ALL DEPRECATED)")
    print(f"   ✅ Time-sensitive from last month should be EXCLUDED from usable_posts")

    # Calculate TRUE usable posts
    print(f"\n✅ TRUE USABLE POSTS CALCULATION:")

    # Criteria for usable posts:
    # 1. Truly evergreen (low urgency, not time-sensitive, not NEWS, not old)
    # 2. Fresh time-sensitive (≤7 days)
    # 3. Not deprecated
    # 4. Has good analysis

    usable_posts = []

    # Add truly evergreen posts (but exclude old ones and DEPRECATED)
    for item in true_evergreen:
        post = item["post"]
        age = item["age"]
        category = (post["category"] or "").upper()

        # EXCLUDE DEPRECATED posts
        if category == "DEPRECATED":
            continue

        # Only include if not too old (let's say < 6 months for safety)
        if age and age["months"] < 6:
            # Check if it has good analysis
            rewrite_score = post["rewrite_score"] or 0.0
            value_score = post["value_score"] or 0.0
            quality_score = post["quality_score"] or 0.0

            if rewrite_score > 0 and value_score > 0 and quality_score > 0:
                usable_posts.append(
                    {
                        "post": post,
                        "reason": "truly_evergreen",
                        "age_months": age["months"],
                    }
                )
        elif not age:
            # If age can't be calculated, check scores and include if good
            rewrite_score = post["rewrite_score"] or 0.0
            value_score = post["value_score"] or 0.0
            quality_score = post["quality_score"] or 0.0

            if rewrite_score > 0 and value_score > 0 and quality_score > 0:
                usable_posts.append(
                    {"post": post, "reason": "truly_evergreen", "age_months": None}
                )

    # Add fresh time-sensitive posts (but exclude DEPRECATED)
    for post in fresh_time_sensitive:
        category = (post["category"] or "").upper()

        # EXCLUDE DEPRECATED posts
        if category == "DEPRECATED":
            continue

        rewrite_score = post["rewrite_score"] or 0.0
        value_score = post["value_score"] or 0.0
        quality_score = post["quality_score"] or 0.0

        if rewrite_score > 0 and value_score > 0 and quality_score > 0:
            created_at = post["created_at"]
            age_days = 0
            if created_at:
                try:
                    created_dt = parse_datetime(created_at)
                    if created_dt:
                        if created_dt.tzinfo:
                            now = datetime.now(created_dt.tzinfo)
                        else:
                            now = datetime.now(timezone.utc)
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        age_days = (now - created_dt).days
                except:
                    pass

            usable_posts.append(
                {"post": post, "reason": "fresh_time_sensitive", "age_days": age_days}
            )

    # Count DEPRECATED posts that were excluded
    deprecated_excluded = 0
    for item in true_evergreen:
        if (item["post"]["category"] or "").upper() == "DEPRECATED":
            deprecated_excluded += 1
    for post in fresh_time_sensitive:
        if (post["category"] or "").upper() == "DEPRECATED":
            deprecated_excluded += 1

    print(
        f"   ✅ Truly evergreen (<6 months, not DEPRECATED): {sum(1 for u in usable_posts if u['reason'] == 'truly_evergreen')}"
    )
    print(
        f"   ✅ Fresh time-sensitive (≤7 days, not DEPRECATED): {sum(1 for u in usable_posts if u['reason'] == 'fresh_time_sensitive')}"
    )
    print(f"   ❌ DEPRECATED posts excluded: {deprecated_excluded}")
    print(
        f"   📊 TOTAL USABLE POSTS: {len(usable_posts)} ({len(usable_posts)/total*100:.1f}% of analyzed posts)"
    )

    # Show age distribution of usable posts
    print(f"\n📅 USABLE POSTS AGE DISTRIBUTION:")
    evergreen_ages = [
        u["age_months"]
        for u in usable_posts
        if u["reason"] == "truly_evergreen" and u["age_months"] is not None
    ]
    fresh_ages = [
        u.get("age_days", 0)
        for u in usable_posts
        if u["reason"] == "fresh_time_sensitive"
    ]

    if evergreen_ages:
        print(
            f"   Evergreen posts: min={min(evergreen_ages):.1f} months, max={max(evergreen_ages):.1f} months, avg={sum(evergreen_ages)/len(evergreen_ages):.1f} months"
        )
    if fresh_ages:
        print(
            f"   Fresh posts: min={min(fresh_ages)} days, max={max(fresh_ages)} days, avg={sum(fresh_ages)/len(fresh_ages):.1f} days"
        )

    # Show category distribution of usable posts
    print(f"\n📊 USABLE POSTS CATEGORY DISTRIBUTION:")
    categories = {}
    for u in usable_posts:
        category = u["post"]["category"] or "UNKNOWN"
        categories[category] = categories.get(category, 0) + 1

    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"   {category}: {count}")

    # Show some examples of false evergreen
    if false_evergreen:
        print(f"\n🔍 EXAMPLES OF FALSE EVERGREEN POSTS (first 5):")
        for i, item in enumerate(false_evergreen[:5]):
            post = item["post"]
            print(f"   {i+1}. Post ID: {post['post_id']}")
            print(f"      Reasons: {', '.join(item['reasons'])}")
            print(
                f"      Urgency: {post['urgency_score'] or 0.0:.2f}, Category: {post['category'] or 'N/A'}"
            )
            if item["age"]:
                print(
                    f"      Age: {item['age']['days']} days ({item['age']['months']:.1f} months)"
                )
            print()

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print(
        f"   1. ❌ EXCLUDE false evergreen posts (high urgency, time_sensitive flag, NEWS category, old)"
    )
    print(f"   2. ❌ EXCLUDE time-sensitive posts from last month (all deprecated)")
    print(
        f"   3. ✅ INCLUDE only truly evergreen posts (<6 months old, low urgency, not time-sensitive)"
    )
    print(f"   4. ✅ INCLUDE fresh time-sensitive posts (≤7 days)")
    print(
        f"   5. 🔍 CONSIDER: Only include evergreen posts < 3 months old for higher quality"
    )

    print(f"\n{'='*80}")

    conn.close()
    return usable_posts, false_evergreen, last_month_deprecated


if __name__ == "__main__":
    analyze_evergreen_accuracy()
