#!/usr/bin/env python3
"""
Web UI for Viewing Rewritten Posts
Simple Flask app to view all scheduled posts
"""
from flask import Flask, render_template, jsonify, request
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

# Directories
SCHEDULED_DIR = Path("scheduled_posts")
CORRECTIONS_DIR = Path("training_data/corrections")
APPROVED_DIR = Path("training_data/approved")

def load_scheduled_posts():
    """Load all scheduled posts"""
    posts = []

    if not SCHEDULED_DIR.exists():
        return posts

    for filepath in SCHEDULED_DIR.glob("*.json"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = json.load(f)
                post['filepath'] = str(filepath)
                posts.append(post)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")

    # Sort by scheduled_for
    posts.sort(key=lambda p: p.get('scheduled_for', ''), reverse=True)

    return posts

def get_stats():
    """Get statistics"""
    posts = load_scheduled_posts()

    stats = {
        'total': len(posts),
        'by_platform': defaultdict(int),
        'by_language': defaultdict(int),
        'by_status': defaultdict(int),
        'corrections': len(list(CORRECTIONS_DIR.glob("*.jsonl"))) if CORRECTIONS_DIR.exists() else 0,
        'approved': len(list(APPROVED_DIR.glob("*.json"))) if APPROVED_DIR.exists() else 0
    }

    for post in posts:
        stats['by_platform'][post.get('platform', 'unknown')] += 1
        stats['by_language'][post.get('language', 'unknown')] += 1
        stats['by_status'][post.get('status', 'scheduled')] += 1

    return stats

@app.route('/')
def index():
    """Main page"""
    posts = load_scheduled_posts()
    stats = get_stats()

    # Get filter params
    platform_filter = request.args.get('platform')
    language_filter = request.args.get('language')
    status_filter = request.args.get('status')

    # Apply filters
    if platform_filter:
        posts = [p for p in posts if p.get('platform') == platform_filter]
    if language_filter:
        posts = [p for p in posts if p.get('language') == language_filter]
    if status_filter:
        posts = [p for p in posts if p.get('status') == status_filter]

    return render_template('index.html',
                         posts=posts,
                         stats=stats,
                         platform_filter=platform_filter,
                         language_filter=language_filter,
                         status_filter=status_filter)

@app.route('/api/posts')
def api_posts():
    """API endpoint for posts"""
    posts = load_scheduled_posts()
    return jsonify(posts)

@app.route('/api/stats')
def api_stats():
    """API endpoint for stats"""
    stats = get_stats()
    return jsonify(stats)

@app.route('/api/post/<post_id>')
def api_post(post_id):
    """Get single post"""
    posts = load_scheduled_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    if post:
        return jsonify(post)
    return jsonify({'error': 'Post not found'}), 404

if __name__ == '__main__':
    # Create templates directory
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    # Create template
    template_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Scheduled Posts - Prismind</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: #1a1a1a;
            border-bottom: 2px solid #2a2a2a;
            padding: 20px 0;
            margin-bottom: 30px;
        }
        h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #888;
            font-size: 14px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 32px;
            font-weight: 600;
            color: #fff;
        }
        .filters {
            background: #1a1a1a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        .filter-group {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .filter-label {
            color: #888;
            font-size: 14px;
        }
        .filter-btn {
            padding: 6px 12px;
            background: #2a2a2a;
            color: #e0e0e0;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            text-decoration: none;
            transition: all 0.2s;
        }
        .filter-btn:hover {
            background: #3a3a3a;
        }
        .filter-btn.active {
            background: #4a9eff;
            border-color: #4a9eff;
            color: #fff;
        }
        .posts-grid {
            display: grid;
            gap: 20px;
        }
        .post-card {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.2s;
        }
        .post-card:hover {
            border-color: #3a3a3a;
            transform: translateY(-2px);
        }
        .post-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        .post-meta {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .badge {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-platform {
            background: #2a4a7c;
            color: #6b9bd1;
        }
        .badge-language {
            background: #3a2a4a;
            color: #b69bd1;
        }
        .badge-priority {
            background: #2a3a2a;
            color: #8bc98b;
        }
        .badge-status {
            background: #4a3a2a;
            color: #d1a96b;
        }
        .post-content {
            color: #c0c0c0;
            font-size: 14px;
            line-height: 1.8;
            margin-bottom: 15px;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
            padding: 15px;
            background: #0f0f0f;
            border-radius: 4px;
            border: 1px solid #2a2a2a;
        }
        .post-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 15px;
            border-top: 1px solid #2a2a2a;
            color: #888;
            font-size: 13px;
        }
        .post-source {
            font-size: 12px;
            color: #666;
        }
        .scheduled-time {
            color: #6b9bd1;
            font-weight: 500;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-state h2 {
            font-size: 24px;
            margin-bottom: 10px;
        }
        .empty-state p {
            font-size: 14px;
        }
        .empty-state code {
            background: #1a1a1a;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>📅 Scheduled Posts</h1>
            <p class="subtitle">Review and manage your rewritten content</p>
        </div>
    </header>

    <div class="container">
        <!-- Stats -->
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Total Posts</div>
                <div class="stat-value">{{ stats.total }}</div>
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

        <!-- Filters -->
        <div class="filters">
            <div class="filter-group">
                <span class="filter-label">Platform:</span>
                <a href="/" class="filter-btn {% if not platform_filter %}active{% endif %}">All</a>
                <a href="/?platform=threads" class="filter-btn {% if platform_filter == 'threads' %}active{% endif %}">Threads</a>
                <a href="/?platform=twitter" class="filter-btn {% if platform_filter == 'twitter' %}active{% endif %}">Twitter</a>
                <a href="/?platform=telegram" class="filter-btn {% if platform_filter == 'telegram' %}active{% endif %}">Telegram</a>
            </div>
            <div class="filter-group">
                <span class="filter-label">Language:</span>
                <a href="/?language=russian" class="filter-btn {% if language_filter == 'russian' %}active{% endif %}">Russian</a>
                <a href="/?language=english" class="filter-btn {% if language_filter == 'english' %}active{% endif %}">English</a>
            </div>
        </div>

        <!-- Posts -->
        {% if posts %}
        <div class="posts-grid">
            {% for post in posts %}
            <div class="post-card">
                <div class="post-header">
                    <div class="post-meta">
                        <span class="badge badge-platform">{{ post.platform }}</span>
                        <span class="badge badge-language">{{ post.language }}</span>
                        <span class="badge badge-priority">Priority: {{ post.priority }}</span>
                        {% if post.status %}
                        <span class="badge badge-status">{{ post.status }}</span>
                        {% endif %}
                    </div>
                </div>

                <div class="post-content">{{ post.rewritten_content }}</div>

                <div class="post-footer">
                    <div>
                        <div class="scheduled-time">📅 {{ post.scheduled_for[:19] }}</div>
                        {% if post.source_post %}
                        <div class="post-source">
                            📎 {{ post.source_post.platform }}: {{ post.source_post.title[:50] }}...
                        </div>
                        {% endif %}
                    </div>
                    <div>
                        {{ post.reason[:60] }}...
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <h2>No scheduled posts yet</h2>
            <p>Start reviewing posts to see them here:</p>
            <p><code>python review_and_publish_from_database.py --limit 5</code></p>
        </div>
        {% endif %}
    </div>
</body>
</html>'''

    with open(templates_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write(template_html)

    print("\n" + "="*100)
    print("🌐 WEB UI STARTING")
    print("="*100)
    print("\n📱 Open in browser: http://localhost:5001")
    print("\n✨ Features:")
    print("   • View all scheduled posts")
    print("   • Filter by platform (Threads/Twitter/Telegram)")
    print("   • Filter by language (Russian/English)")
    print("   • See statistics and trends")
    print("\n" + "="*100 + "\n")

    app.run(debug=True, port=5001, host='0.0.0.0')
