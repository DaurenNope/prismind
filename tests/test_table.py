#!/usr/bin/env python3
"""
Test if the posts table exists and insert test data
"""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not supabase_url or not supabase_key:
    print("❌ Missing Supabase credentials")
    exit(1)

# Create Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

try:
    # Try to query the posts table
    result = supabase.table('posts').select('*').limit(1).execute()
    print("✅ Posts table exists!")
    print(f"Found {len(result.data)} records")
    
    # Insert a test record
    test_data = {
        'id': 999999,
        'title': 'Test Post',
        'content': 'This is a test post to verify the table structure.',
        'platform': 'test',
        'author': 'Test Author',
        'author_handle': '@testauthor',
        'url': 'https://example.com/test',
        'summary': 'Test summary',
        'value_score': 5,
        'smart_tags': '["test", "verification"]',
        'ai_summary': 'This is a test AI summary.',
        'folder_category': 'test',
        'category': 'test'
    }
    
    result = supabase.table('posts').upsert(test_data).execute()
    print("✅ Test record inserted successfully!")
    
    # Query again to verify
    result = supabase.table('posts').select('*').execute()
    print(f"✅ Table now has {len(result.data)} records")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("The posts table doesn't exist yet.")
    print("Please create it manually in the Supabase dashboard:")
    print("1. Go to your Supabase dashboard")
    print("2. Click on 'SQL Editor'")
    print("3. Run the SQL from scripts/supabase_setup.sql") 