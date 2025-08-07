#!/usr/bin/env python3
"""
Example usage of SupabaseManager
Shows how to integrate it into your existing code
"""

from supabase_manager import SupabaseManager

def main():
    # Initialize the database manager
    db = SupabaseManager()
    
    # Example 1: Insert a new post
    new_post = {
        'id': 1001,
        'title': 'My First Post',
        'content': 'This is the content of my first post using the database manager.',
        'platform': 'reddit',
        'author': 'John Doe',
        'author_handle': '@johndoe',
        'url': 'https://reddit.com/r/example/123',
        'summary': 'A summary of my first post',
        'value_score': 7,
        'smart_tags': 'reddit,example,first-post',
        'ai_summary': 'This is an example post created using the SupabaseManager.',
        'folder_category': 'personal',
        'category': 'general'
    }
    
    print("📝 Inserting new post...")
    inserted_post = db.insert_post(new_post)
    if inserted_post:
        print(f"✅ Inserted: {inserted_post['title']}")
    
    # Example 2: Get posts by platform
    print("\n📋 Getting Reddit posts...")
    reddit_posts = db.get_posts(platform='reddit', limit=5)
    print(f"Found {len(reddit_posts)} Reddit posts")
    
    # Example 3: Search for posts
    print("\n🔍 Searching for 'post'...")
    search_results = db.search_posts('post', limit=3)
    print(f"Found {len(search_results)} posts containing 'post'")
    
    # Example 4: Update a post
    print("\n✏️  Updating post value score...")
    updated_post = db.update_post(1001, {'value_score': 9})
    if updated_post:
        print(f"✅ Updated: {updated_post['title']} (Score: {updated_post['value_score']})")
    
    # Example 5: Get top posts
    print("\n🏆 Getting top posts...")
    top_posts = db.get_top_posts(limit=5)
    print(f"Found {len(top_posts)} top posts")
    for i, post in enumerate(top_posts, 1):
        print(f"  {i}. {post.get('title', 'No title')} (Score: {post.get('value_score', 0)})")
    
    # Example 6: Get posts by category
    print("\n📂 Getting posts by category...")
    general_posts = db.get_posts_by_category('general', limit=3)
    print(f"Found {len(general_posts)} posts in 'general' category")

if __name__ == "__main__":
    main() 