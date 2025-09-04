#!/usr/bin/env python3
"""
Clean duplicate posts from database
"""

from scripts.supabase_manager import SupabaseManager

def clean_duplicates():
    """Remove duplicate posts based on content"""
    
    print("🧹 Cleaning Duplicate Posts")
    print("=" * 40)
    
    # Initialize database manager
    db_manager = SupabaseManager()
    
    # Get all posts
    print("📊 Fetching all posts...")
    all_posts = db_manager.get_posts(limit=1000)
    
    if not all_posts:
        print("❌ No posts found")
        return
    
    print(f"📊 Found {len(all_posts)} total posts")
    
    # Find duplicates by content
    content_groups = {}
    duplicates_to_remove = []
    
    for post in all_posts:
        content = post.get('content', '').strip()
        if content:
            if content not in content_groups:
                content_groups[content] = [post]
            else:
                content_groups[content].append(post)
    
    # Identify duplicates (keep the first one, remove the rest)
    for content, posts in content_groups.items():
        if len(posts) > 1:
            # Keep the first post, mark the rest for deletion
            for post in posts[1:]:
                duplicates_to_remove.append(post)
    
    print(f"🔍 Found {len(duplicates_to_remove)} duplicate posts to remove")
    print(f"📝 Will keep {len(content_groups)} unique posts")
    
    if not duplicates_to_remove:
        print("✅ No duplicates found!")
        return
    
    # Show some examples
    print("\n📝 Sample duplicates to remove:")
    for i, post in enumerate(duplicates_to_remove[:5]):
        content = post.get('content', '')[:50]
        print(f"  {i+1}. ID: {post.get('id')} - \"{content}...\"")
    
    # Ask for confirmation
    print(f"\n⚠️  About to delete {len(duplicates_to_remove)} duplicate posts")
    response = input("Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ Cancelled")
        return
    
    # Remove duplicates
    print("\n🗑️  Removing duplicates...")
    removed_count = 0
    
    for post in duplicates_to_remove:
        try:
            post_id = post.get('id')
            if db_manager.delete_post(post_id):
                removed_count += 1
                print(f"✅ Removed duplicate ID: {post_id}")
            else:
                print(f"❌ Failed to remove ID: {post_id}")
        except Exception as e:
            print(f"❌ Error removing ID {post.get('id')}: {e}")
    
    print("\n🎉 Cleanup complete!")
    print(f"✅ Removed {removed_count} duplicate posts")
    print(f"📊 Database now has {len(all_posts) - removed_count} unique posts")

if __name__ == "__main__":
    clean_duplicates()


