#!/usr/bin/env python3
"""Verify truncation detection - show actual content endings"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.manager import SupabaseManager

sb = SupabaseManager()
client = sb.client

response = (
    client.table("posts")
    .select("post_id, content")
    .eq("platform", "twitter")
    .order("collected_at", desc=True)
    .limit(20)
    .execute()
)

print("Verifying truncation - showing actual content endings:\n")
print("=" * 80)

# The 13 posts I flagged as truncated
truncated_ids = [
    "twitter_1987968082971676762",
    "twitter_1987923137929818555",
    "twitter_1987983866473357372",
    "twitter_1988065880870195248",
    "twitter_1988000940050288927",
    "twitter_1988228002509971672",
    "twitter_1988065931696939464",
    "twitter_1987999761748877572",
    "twitter_1988064701075648776",
    "twitter_1988954763862634627",
    "twitter_1989035898948747738",
    "twitter_1980307485719429602",
    "twitter_1980233080213590326",
]

for post in response.data:
    post_id = post.get("post_id", "unknown")
    if post_id not in truncated_ids:
        continue

    content = post.get("content", "") or ""

    if not content:
        continue

    last_150 = content[-150:] if len(content) > 150 else content
    last_char = content[-1] if content else ""
    last_10 = content[-10:] if len(content) > 10 else content

    # Check if it actually looks truncated
    ends_lowercase = last_char.islower() and last_char.isalpha()
    ends_comma = content.rstrip().endswith(",")
    ends_ellipsis = content.rstrip().endswith("...") or content.rstrip().endswith("…")

    print(f"\n{post_id}:")
    print(f"   Length: {len(content)} chars")
    print(f"   Last 150 chars:")
    print(f"   {repr(last_150)}")
    print(f"   Last 10 chars: {repr(last_10)}")
    print(f"   Last char: {repr(last_char)}")
    print(f"   Ends lowercase: {ends_lowercase}")
    print(f"   Ends comma: {ends_comma}")
    print(f"   Ends ellipsis: {ends_ellipsis}")
    print(
        f"   Looks truncated: {ends_ellipsis or (ends_lowercase and len(content) > 50) or ends_comma}"
    )
