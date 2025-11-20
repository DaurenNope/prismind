#!/usr/bin/env python3
"""
Delete posts from the local SQLite cache (beyondlines.db) and Supabase.

Examples:
  # Preview Threads posts collected after a timestamp (no deletion)
  python scripts/delete_posts.py --platform threads --since "2025-11-18T16:40:00" --dry-run

  # Delete specific post IDs from both stores
  python scripts/delete_posts.py --platform threads --post-ids threads_DP1PIMyDGBf,threads_DQmohPOjb3h

  # Delete the most recent 20 Threads posts containing a phrase
  python scripts/delete_posts.py --platform threads --contains "Threads User" --limit 20
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Sequence

from dotenv import load_dotenv

try:
    from supabase import create_client
except ImportError:  # pragma: no cover - optional dependency
    create_client = None


DB_PATH = Path("beyondlines.db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete posts from local DB and Supabase.")
    parser.add_argument("--platform", required=True, help="Platform name (e.g., threads, twitter)")
    parser.add_argument(
        "--post-ids",
        help="Comma-separated list of post_ids to delete (overrides other filters)",
    )
    parser.add_argument(
        "--authors",
        help="Comma-separated list of author usernames/handles to filter by",
    )
    parser.add_argument(
        "--contains",
        help="Substring that must appear in the content/title (case-insensitive)",
    )
    parser.add_argument(
        "--since",
        help="ISO timestamp (e.g., 2025-11-18T16:40:00) to delete posts created at/after this time",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of posts to delete (after filters). Default: all matches",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show matching posts without deleting anything",
    )
    parser.add_argument(
        "--supabase-only",
        action="store_true",
        help="Only delete from Supabase (skip local SQLite)",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Only delete from local SQLite (skip Supabase)",
    )
    return parser.parse_args()


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def fetch_local_posts(
    platform: str,
    author_filters: Sequence[str],
    content_substring: str | None,
    since_iso: str | None,
    limit: int | None,
) -> List[Dict[str, str]]:
    if not DB_PATH.exists():
        print(f"⚠️  Local database {DB_PATH} not found; skipping SQLite scan.")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        clauses = ["platform = ?"]
        params: List[str] = [platform]

        if author_filters:
            placeholders = ",".join("?" for _ in author_filters)
            clauses.append(f"author IN ({placeholders})")
            params.extend(author_filters)

        if content_substring:
            clauses.append("(content LIKE ? OR title LIKE ?)")
            like = f"%{content_substring}%"
            params.extend([like, like])

        if since_iso:
            clauses.append("created_at >= ?")
            params.append(since_iso)

        where_sql = " AND ".join(clauses)
        sql = (
            "SELECT post_id, author, title, substr(content, 1, 120) AS snippet, created_at "
            "FROM posts "
            f"WHERE {where_sql} "
            "ORDER BY created_at DESC"
        )
        if limit:
            sql += f" LIMIT {int(limit)}"

        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_from_sqlite(platform: str, post_ids: Sequence[str]) -> int:
    if not post_ids or not DB_PATH.exists():
        return 0
    conn = sqlite3.connect(DB_PATH)
    try:
        placeholders = ",".join("?" for _ in post_ids)
        params = list(post_ids)
        params.append(platform)
        sql = f"DELETE FROM posts WHERE post_id IN ({placeholders}) AND platform = ?"
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_from_supabase(platform: str, post_ids: Sequence[str]) -> int:
    if not post_ids:
        return 0

    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("⚠️  Supabase credentials not found; skipping Supabase deletion.")
        return 0
    if create_client is None:
        print("⚠️  supabase-py not installed; cannot delete from Supabase.")
        return 0

    client = create_client(url, key)
    total_deleted = 0
    chunk_size = 50
    for i in range(0, len(post_ids), chunk_size):
        chunk = post_ids[i : i + chunk_size]
        resp = (
            client.table("posts")
            .delete()
            .eq("platform", platform)
            .in_("post_id", chunk)
            .execute()
        )
        total_deleted += len(resp.data or [])
    return total_deleted


def main() -> None:
    args = parse_args()

    explicit_ids = _split_csv(args.post_ids)
    author_filters = _split_csv(args.authors)

    matches = fetch_local_posts(
        platform=args.platform,
        author_filters=author_filters,
        content_substring=args.contains,
        since_iso=args.since,
        limit=args.limit if explicit_ids else args.limit,
    )

    if matches:
        print(f"🔎 Found {len(matches)} local {args.platform} posts matching filters:")
        for row in matches:
            snippet = (row.get("snippet") or "").replace("\n", " ").strip()
            print(
                f"  - {row['post_id']} | {row.get('author','?')} | {row.get('created_at','?')} | {snippet}"
            )
    else:
        print("ℹ️  No matching posts found in local SQLite cache.")

    target_ids = list(dict.fromkeys(explicit_ids or [row["post_id"] for row in matches]))
    if not target_ids:
        print("⚠️  No post IDs to delete. Supply --post-ids or adjust filters.")
        return

    print(f"\n🗑  Targeting {len(target_ids)} post(s): {', '.join(target_ids[:10])}")
    if len(target_ids) > 10:
        print("    ...")

    if args.dry_run:
        print("Dry-run enabled; no deletions performed.")
        return

    total_local = 0
    total_remote = 0

    if not args.supabase_only:
        total_local = delete_from_sqlite(args.platform, target_ids)
        print(f"✅ Deleted {total_local} rows from beyondlines.db")

    if not args.local_only:
        total_remote = delete_from_supabase(args.platform, target_ids)
        print(f"✅ Deleted {total_remote} rows from Supabase")

    print(
        f"\nDone. Removed {total_local} local rows and {total_remote} Supabase rows for platform '{args.platform}'."
    )


if __name__ == "__main__":
    main()


