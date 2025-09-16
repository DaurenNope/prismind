#!/usr/bin/env python3
"""Test Supabase connection and basic operations."""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

def main():
    """Test Supabase connection and basic operations."""
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Error: Missing Supabase URL or Service Role Key in .env file")
        sys.exit(1)
    
    print("🔌 Testing Supabase connection...")
    
    try:
        # Initialize the client
        supabase = create_client(url, key)
        
        # Try to get the first 5 posts
        print("\n📋 Fetching first 5 posts from Supabase...")
        result = supabase.table('posts').select('*').limit(5).execute()
        
        if hasattr(result, 'error') and result.error:
            print(f"❌ Error fetching posts: {result.error}")
        else:
            print(f"✅ Found {len(result.data)} posts")
            for i, post in enumerate(result.data, 1):
                print(f"\n📄 Post {i}:")
                print(f"   ID: {post.get('id')}")
                print(f"   Title: {post.get('title', 'No title')}")
                print(f"   URL: {post.get('url', 'No URL')}")
        
        # Try to insert a test post with a unique URL
        import uuid
        test_url = f"https://example.com/test-{uuid.uuid4()}"
        
        print("\n🧪 Testing post insertion...")
        test_data = {
            'title': 'Test Post from Script',
            'content': 'This is a test post from the sync script',
            'platform': 'test',
            'author': 'sync_script',
            'author_handle': 'sync_script',
            'url': test_url,  # Use a unique URL
            'summary': 'Test summary',
            'ai_summary': 'Test AI summary',
            'value_score': 0,
            'smart_tags': 'test,integration',
            'folder_category': 'test',
            'category': 'test',
            'created_at': 'now()'  # Let Supabase handle the timestamp
        }
        
        result = supabase.table('posts').insert(test_data).execute()
        
        if hasattr(result, 'error') and result.error:
            print(f"❌ Error inserting test post: {result.error}")
        else:
            print("✅ Successfully inserted test post")
            if hasattr(result, 'data') and result.data:
                print(f"   ID: {result.data[0].get('id')}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
