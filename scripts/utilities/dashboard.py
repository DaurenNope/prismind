#!/usr/bin/env python3
"""
Prismind Dashboard - Unified Web UI
All features in one place: review posts, view scheduled, see trends, approve content
"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for

load_dotenv(override=True)

from src.domain.intelligence.trend_analyzer import TrendAnalyzer
from src.domain.publishing.modular_rewriter.compat import create_compat_rewriter
from src.domain.publishing.scheduler import PublishingScheduler
from src.infrastructure.database.storage.db import StorageFacade

app = Flask(__name__)

# Directories
SCHEDULED_DIR = Path("scheduled_posts")
CORRECTIONS_DIR = Path("training_data/corrections")
APPROVED_DIR = Path("training_data/approved")

# Initialize services
db = StorageFacade()
rewriter = create_compat_rewriter()
scheduler = PublishingScheduler()
trend_analyzer = TrendAnalyzer()

# Language routing
LANGUAGE_MAP = {
    "threads": "russian",
    "twitter": "english",
    "telegram": "russian",
    "reddit": "english",
}

OUTPUT_PLATFORMS = {
    "threads": "threads",
    "twitter": "twitter",
    "reddit": "threads",
    "telegram": "telegram",
}


def load_scheduled_posts():
    """Load all scheduled posts"""
    posts = []
    if not SCHEDULED_DIR.exists():
        return posts

    for filepath in SCHEDULED_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                post = json.load(f)
                post["filepath"] = str(filepath)
                posts.append(post)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")

    posts.sort(key=lambda p: p.get("scheduled_for", ""), reverse=True)
    return posts


def get_stats():
    """Get statistics"""
    posts = load_scheduled_posts()

    stats = {
        "total_scheduled": len(posts),
        "by_platform": defaultdict(int),
        "by_language": defaultdict(int),
        "corrections": len(list(CORRECTIONS_DIR.glob("*.jsonl")))
        if CORRECTIONS_DIR.exists()
        else 0,
        "approved": len(list(APPROVED_DIR.glob("*.json")))
        if APPROVED_DIR.exists()
        else 0,
        "database_posts": 673,  # From your database
    }

    for post in posts:
        stats["by_platform"][post.get("platform", "unknown")] += 1
        stats["by_language"][post.get("language", "unknown")] += 1

    return stats


@app.route("/")
def index():
    """Main dashboard"""
    stats = get_stats()
    return render_template("dashboard.html", stats=stats, page="dashboard")


@app.route("/scheduled")
def scheduled_posts():
    """View scheduled posts"""
    posts = load_scheduled_posts()
    stats = get_stats()

    platform_filter = request.args.get("platform")
    language_filter = request.args.get("language")

    if platform_filter:
        posts = [p for p in posts if p.get("platform") == platform_filter]
    if language_filter:
        posts = [p for p in posts if p.get("language") == language_filter]

    return render_template(
        "scheduled.html",
        posts=posts,
        stats=stats,
        platform_filter=platform_filter,
        language_filter=language_filter,
        page="scheduled",
    )


@app.route("/review")
def review_page():
    """Review posts from database"""
    stats = get_stats()
    return render_template("review.html", stats=stats, page="review")


@app.route("/api/queue", methods=["GET"])
def api_get_queue():
    """Get posts from database for review"""
    limit = int(request.args.get("limit", 5))
    platform = request.args.get("platform")

    # Fetch from database
    all_posts = db.get_posts(limit=limit * 3)
    posts = []

    for post in all_posts:
        if post is None:
            continue
        if platform and post.get("platform") != platform:
            continue
        posts.append(post)
        if len(posts) >= limit:
            break

    return jsonify({"posts": posts, "count": len(posts)})


@app.route("/api/rewrite", methods=["POST"])
def api_rewrite():
    """Generate rewrite for a post"""
    data = request.json
    post = data.get("post")

    if not post:
        return jsonify({"error": "No post provided"}), 400

    # Determine language and platform
    source_platform = post.get("platform", "unknown")
    output_platform = OUTPUT_PLATFORMS.get(source_platform, "threads")
    language = LANGUAGE_MAP.get(output_platform, "russian")

    try:
        # Simple analysis
        analyzed = {
            "content": post.get("content", ""),
            "category": "Technology",
            "summary": post.get("content", "")[:200],
            "key_concepts": [],
            "topics": [],
            "rewrite_angles": [
                {
                    "persona": "qronoya",
                    "angle": f"Rewrite in Qronoya voice",
                    "tone": "Natural",
                    "platform_fit": output_platform,
                }
            ],
        }

        # Generate rewrite (synchronous wrapper for async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            rewriter.rewrite_analyzed_post(
                analyzed_content=analyzed,
                persona="qronoya",
                platform=output_platform,
                language=language,
            )
        )
        loop.close()

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        return jsonify(
            {
                "rewritten_content": result.get("rewritten_content", ""),
                "platform": output_platform,
                "language": language,
                "source_post": post,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/approve", methods=["POST"])
def api_approve():
    """Approve and schedule a rewrite"""
    data = request.json

    rewritten_content = data.get("rewritten_content")
    platform = data.get("platform")
    language = data.get("language")
    source_post = data.get("source_post")

    if not rewritten_content:
        return jsonify({"error": "No content"}), 400

    try:
        # Schedule
        decision = scheduler.schedule_rewritten_post(
            rewritten_content={
                "rewritten_content": rewritten_content,
                "viral_potential": 50,
                "time_sensitivity": "evergreen",
                "platform": platform,
            },
            platform_override=platform,
        )

        # Save scheduled post
        scheduled_post = {
            "id": f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "source_post": source_post,
            "rewritten_content": rewritten_content,
            "platform": platform,
            "language": language,
            "persona": "qronoya",
            "scheduled_for": decision.when.isoformat(),
            "priority": decision.priority,
            "reason": decision.reason,
            "status": "approved",
            "metadata": {"approved_at": datetime.now().isoformat()},
        }

        SCHEDULED_DIR.mkdir(exist_ok=True)
        filepath = SCHEDULED_DIR / f"{scheduled_post['id']}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scheduled_post, f, ensure_ascii=False, indent=2)

        # Log approval
        APPROVED_DIR.mkdir(parents=True, exist_ok=True)
        count = len(list(APPROVED_DIR.glob("qronoya_*.json"))) + 1
        approved_file = APPROVED_DIR / f"qronoya_approved_{count:03d}.json"
        with open(approved_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "id": f"approved_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.now().isoformat(),
                    "source_post": source_post,
                    "gemini_output": rewritten_content,
                    "platform": platform,
                    "language": language,
                    "status": "approved",
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        return jsonify(
            {
                "success": True,
                "scheduled_for": decision.when.isoformat(),
                "priority": decision.priority,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reject", methods=["POST"])
def api_reject():
    """Reject a rewrite"""
    data = request.json

    source_post = data.get("source_post")
    rewritten_content = data.get("rewritten_content")
    reason = data.get("reason", "")

    try:
        # Log rejection
        CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = CORRECTIONS_DIR / f"{date_str}_corrections.jsonl"

        rejection_data = {
            "id": f"rejected_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "source_post": source_post,
            "gemini_output": rewritten_content,
            "persona": "qronoya",
            "status": "rejected",
            "rejection_reason": reason,
        }

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(rejection_data, ensure_ascii=False) + "\n")

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/trends")
def trends_page():
    """Trend analysis page"""
    stats = get_stats()

    # Run trend analysis
    try:
        all_posts = db.get_posts(limit=200)
        posts = [p for p in all_posts if p is not None]

        analysis = trend_analyzer.analyze_trends(posts, time_window_hours=72)
    except Exception as e:
        analysis = {"error": str(e), "trending_topics": [], "content_suggestions": []}

    return render_template("trends.html", stats=stats, analysis=analysis, page="trends")


if __name__ == "__main__":
    # Create templates directory
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    # Create base template
    base_template = """<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Prismind Dashboard{% endblock %}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            line-height: 1.6;
        }
        .navbar {
            background: #1a1a1a;
            border-bottom: 2px solid #2a2a2a;
            padding: 0;
        }
        .nav-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            gap: 30px;
            padding: 0 20px;
        }
        .brand {
            font-size: 20px;
            font-weight: 700;
            padding: 20px 0;
            color: #4a9eff;
            text-decoration: none;
        }
        .nav-links {
            display: flex;
            gap: 0;
            flex: 1;
        }
        .nav-link {
            padding: 20px 20px;
            color: #888;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }
        .nav-link:hover {
            color: #e0e0e0;
            background: #1f1f1f;
        }
        .nav-link.active {
            color: #4a9eff;
            border-bottom-color: #4a9eff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px 20px;
        }
        .page-header {
            margin-bottom: 30px;
        }
        .page-title {
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .page-subtitle {
            color: #888;
            font-size: 15px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #2a2a2a;
        }
        .stat-label {
            color: #888;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .stat-value {
            font-size: 36px;
            font-weight: 700;
            color: #fff;
        }
        .btn {
            padding: 10px 20px;
            background: #4a9eff;
            color: #fff;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            background: #3a8eef;
            transform: translateY(-1px);
        }
        .btn-secondary {
            background: #2a2a2a;
            color: #e0e0e0;
        }
        .btn-secondary:hover {
            background: #3a3a3a;
        }
        .btn-danger {
            background: #ef4444;
        }
        .btn-danger:hover {
            background: #dc2626;
        }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
    <nav class="navbar">
        <div class="nav-content">
            <a href="/" class="brand">🎯 Prismind</a>
            <div class="nav-links">
                <a href="/" class="nav-link {% if page == 'dashboard' %}active{% endif %}">Dashboard</a>
                <a href="/review" class="nav-link {% if page == 'review' %}active{% endif %}">Review Posts</a>
                <a href="/scheduled" class="nav-link {% if page == 'scheduled' %}active{% endif %}">Scheduled</a>
                <a href="/trends" class="nav-link {% if page == 'trends' %}active{% endif %}">Trends</a>
            </div>
        </div>
    </nav>

    {% block content %}{% endblock %}

    {% block extra_js %}{% endblock %}
</body>
</html>"""

    with open(templates_dir / "base.html", "w") as f:
        f.write(base_template)

    # Dashboard template
    dashboard_template = """{% extends "base.html" %}

{% block content %}
<div class="container">
    <div class="page-header">
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Your intelligent content publishing system</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Database Posts</div>
            <div class="stat-value">{{ stats.database_posts }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Scheduled</div>
            <div class="stat-value">{{ stats.total_scheduled }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Corrections</div>
            <div class="stat-value">{{ stats.corrections }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Approved</div>
            <div class="stat-value">{{ stats.approved }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Threads (RU)</div>
            <div class="stat-value">{{ stats.by_platform.threads or 0 }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Twitter (EN)</div>
            <div class="stat-value">{{ stats.by_platform.twitter or 0 }}</div>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
        <div style="background: #1a1a1a; padding: 30px; border-radius: 8px; border: 1px solid #2a2a2a;">
            <h3 style="font-size: 20px; margin-bottom: 15px;">📝 Review Posts</h3>
            <p style="color: #888; margin-bottom: 20px;">Review database posts and approve/edit rewrites</p>
            <a href="/review" class="btn">Start Reviewing</a>
        </div>

        <div style="background: #1a1a1a; padding: 30px; border-radius: 8px; border: 1px solid #2a2a2a;">
            <h3 style="font-size: 20px; margin-bottom: 15px;">📅 Scheduled Posts</h3>
            <p style="color: #888; margin-bottom: 20px;">View all scheduled posts ready for publishing</p>
            <a href="/scheduled" class="btn">View Schedule</a>
        </div>

        <div style="background: #1a1a1a; padding: 30px; border-radius: 8px; border: 1px solid #2a2a2a;">
            <h3 style="font-size: 20px; margin-bottom: 15px;">📈 Trends</h3>
            <p style="color: #888; margin-bottom: 20px;">See what's trending and get content suggestions</p>
            <a href="/trends" class="btn">View Trends</a>
        </div>
    </div>
</div>
{% endblock %}"""

    with open(templates_dir / "dashboard.html", "w") as f:
        f.write(dashboard_template)

    print("\n" + "=" * 100)
    print("🚀 PRISMIND DASHBOARD STARTING")
    print("=" * 100)
    print("\n🌐 Open in browser: http://localhost:5000")
    print("\n✨ Features:")
    print("   • Dashboard - Overview and quick actions")
    print("   • Review Posts - Interactive review from database")
    print("   • Scheduled - View all scheduled posts")
    print("   • Trends - See trending topics + content suggestions")
    print("\n" + "=" * 100 + "\n")

    app.run(debug=True, port=5000, host="0.0.0.0")
