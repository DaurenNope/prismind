#!/usr/bin/env python3
"""Remove stray Twitter feed posts that were accidentally ingested.

This script deletes the known November 10 non-bookmark tweets from both the
local SQLite cache and the Supabase `posts` table. Update the `TARGET_AUTHORS`
set or the `TARGET_SNIPPETS` list if additional clean-up is required.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Iterable

from supabase import create_client

# Authors and content snippets of the stray tweets we want to purge.
TARGET_AUTHORS = {
    "DITOGAMES",
    "Geomi",
    "Sui",
    "DigiShares",
}

TARGET_SNIPPETS = [
    "If you have a mouse, you have to play this game",
    "AI copilot for building on Aptos",
    "BTC is booming on Sui",
    "webinar is coming! Join us on November 12, 2025",
]


def delete_from_sqlite(db_path: str = "beyondlines.db") -> int:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            DELETE FROM posts
            WHERE platform = 'twitter'
              AND (author IN ({','.join('?' for _ in TARGET_AUTHORS)})
                   OR { ' OR '.join(['content LIKE ?' for _ in TARGET_SNIPPETS]) })
            """,
            (*TARGET_AUTHORS, *[f"%{snippet}%" for snippet in TARGET_SNIPPETS]),
        )
        deleted = cursor.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()


def delete_from_supabase() -> int:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        print(
            "⚠️  SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/KEY not set; skipping Supabase deletion"
        )
        return 0

    client = create_client(url, key)

    # Delete by author first
    response = (
        client.table("posts")
        .delete()
        .eq("platform", "twitter")
        .in_("author", list(TARGET_AUTHORS))
        .execute()
    )
    deleted = len(response.data or [])

    # Delete any lingering rows by snippet match (case insensitive illike)
    for snippet in TARGET_SNIPPETS:
        resp = (
            client.table("posts")
            .delete()
            .eq("platform", "twitter")
            .ilike("content", f"%{snippet}%")
            .execute()
        )
        deleted += len(resp.data or [])

    return deleted


def main() -> None:
    sqlite_deleted = delete_from_sqlite()
    supabase_deleted = delete_from_supabase()

    print(f"✅ Removed {sqlite_deleted} rows from local SQLite cache")
    if supabase_deleted:
        print(f"✅ Removed {supabase_deleted} rows from Supabase posts table")
    else:
        print("ℹ️  No Supabase rows deleted (credentials missing or no matches)")


if __name__ == "__main__":
    main()
