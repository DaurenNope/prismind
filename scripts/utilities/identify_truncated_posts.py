#!/usr/bin/env python3
"""
Identify truly truncated posts that need re-collection
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.manager import SupabaseManager

def identify_truncated_posts():
    """Identify posts that are actually truncated and need re-collection"""
    
    supabase = SupabaseManager()
    client = supabase.client
    
    print("=" * 60)
    print("Identifying Truncated Posts for Re-collection")
    print("=" * 60)
    
    platforms = ["twitter", "threads", "reddit"]
    
    for platform in platforms:
        print(f"\n{'='*60}")
        print(f"📊 {platform.upper()} - Truncated Posts")
        print(f"{'='*60}\n")
        
        # Get recent posts
        result = (
            client.table("posts")
            .select("post_id, author, content, url, collected_at")
            .eq("platform", platform)
            .order("collected_at", desc=True)
            .limit(100)
            .execute()
        )
        
        posts = result.data or []
        
        if not posts:
            print(f"⚠️  No {platform} posts found")
            continue
        
        truly_truncated = []
        likely_complete = []
        
        for post in posts:
            post_id = post.get("post_id", "N/A")
            content = post.get("content", "")
            url = post.get("url", "N/A")
            collected_at = post.get("collected_at", "N/A")
            
            if not content:
                continue
            
            content_length = len(content)
            content_lower = content.lower()
            
            # Strong indicators of truncation
            strong_indicators = [
                content.rstrip().endswith("..."),
                content.rstrip().endswith("…"),
                "show more" in content_lower[-50:],  # At the end
                "read more" in content_lower[-50:],
                "continue reading" in content_lower[-50:],
            ]
            
            # Medium indicators (might be truncation)
            medium_indicators = [
                content_length < 100 and ("..." in content or "…" in content),
                content_length > 200 and not any(p in content[-30:] for p in ['.', '!', '?', '…', ')', ']', '}']),
                content_length > 500 and content.rstrip().endswith("..."),
            ]
            
            # Check if it's a quote/retweet (these often have "..." in the middle)
            is_quote = ">" in content[:50] or content.startswith("RT ") or content.startswith("QT ")
            
            # Determine if truly truncated
            is_truncated = False
            reason = None
            
            if any(strong_indicators):
                is_truncated = True
                if content.rstrip().endswith("..."):
                    reason = "Ends with '...'"
                elif content.rstrip().endswith("…"):
                    reason = "Ends with '…'"
                elif "show more" in content_lower[-50:]:
                    reason = "Contains 'Show more' at end"
                elif "read more" in content_lower[-50:]:
                    reason = "Contains 'Read more' at end"
            elif any(medium_indicators) and not is_quote:
                # Medium indicators but not a quote
                if content_length < 100:
                    is_truncated = True
                    reason = "Very short with ellipsis"
                elif content_length > 200 and not any(p in content[-30:] for p in ['.', '!', '?']):
                    is_truncated = True
                    reason = "Long content without proper ending"
            
            if is_truncated:
                truly_truncated.append({
                    "post_id": post_id,
                    "reason": reason,
                    "length": content_length,
                    "url": url,
                    "collected_at": collected_at,
                    "preview": content[:150] + "..." if len(content) > 150 else content
                })
            else:
                # Likely complete
                likely_complete.append({
                    "post_id": post_id,
                    "length": content_length,
                    "has_ellipsis": "..." in content or "…" in content
                })
        
        print(f"📈 Analysis Results:")
        print(f"   Total posts checked: {len(posts)}")
        print(f"   ✅ Likely complete: {len(likely_complete)}")
        print(f"   ⚠️  Truncated (needs re-collection): {len(truly_truncated)}")
        
        if truly_truncated:
            print(f"\n⚠️  Truncated Posts That Need Re-collection:")
            print(f"{'='*60}")
            
            # Group by reason
            by_reason = {}
            for item in truly_truncated:
                reason = item["reason"]
                if reason not in by_reason:
                    by_reason[reason] = []
                by_reason[reason].append(item)
            
            for reason, items in sorted(by_reason.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"\n{reason} ({len(items)} posts):")
                for item in items[:10]:  # Show first 10 of each type
                    print(f"   - {item['post_id']}")
                    print(f"     Length: {item['length']} chars")
                    print(f"     URL: {item['url']}")
                    print(f"     Collected: {item['collected_at']}")
                    print(f"     Preview: {item['preview']}")
                    print()
                
                if len(items) > 10:
                    print(f"     ... and {len(items) - 10} more")
            
            # Summary for re-collection
            print(f"\n{'='*60}")
            print(f"📋 Re-collection Summary:")
            print(f"{'='*60}")
            print(f"Total posts needing re-collection: {len(truly_truncated)}")
            print(f"\nPost IDs to re-collect:")
            post_ids = [item['post_id'] for item in truly_truncated]
            print(f"  {', '.join(post_ids[:20])}")
            if len(post_ids) > 20:
                print(f"  ... and {len(post_ids) - 20} more")
        else:
            print(f"\n✅ No truncated posts found! All posts appear to be complete.")
        
        # Show completion rate
        completion_rate = (len(likely_complete) / len(posts) * 100) if posts else 0
        print(f"\n📊 Completion Rate: {completion_rate:.1f}%")
        if completion_rate >= 90:
            print("✅ Excellent - Most posts are complete!")
        elif completion_rate >= 70:
            print("⚠️  Good - Some posts need re-collection")
        else:
            print("❌ Poor - Many posts need re-collection")

if __name__ == "__main__":
    identify_truncated_posts()

