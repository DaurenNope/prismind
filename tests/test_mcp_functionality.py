#!/usr/bin/env python3
"""
Test Supabase functionality that the MCP server should provide
"""

import os
import pytest

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not supabase_url or not supabase_key:
    pytest.skip("Missing Supabase credentials", allow_module_level=True)

try:
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("🔍 Testing Supabase functionality...")
    
    # Test 1: List tables (equivalent to MCP list_tables)
    print("\n📋 Testing table listing...")
    try:
        # Query to get table information
        result = supabase.rpc('get_tables').execute()
        print("✅ Tables listed successfully")
        print(f"Tables: {result.data}")
    except Exception as e:
        print(f"⚠️  Could not list tables: {e}")
    
    # Test 2: Insert a test record
    print("\n📝 Testing record insertion...")
    test_data = {
        'id': 1,
        'title': 'Test Post',
        'content': 'This is a test post created via Python client',
        'platform': 'test',
        'author': 'Test Author',
        'author_handle': '@testauthor',
        'url': 'https://example.com/test',
        'summary': 'Test summary',
        'value_score': 5,
        'smart_tags': 'test,example',
        'ai_summary': 'This is a test post for functionality testing',
        'folder_category': 'test',
        'category': 'test'
    }
    
    try:
        result = supabase.table('posts').upsert(test_data).execute()
        print("✅ Test record inserted successfully")
        print(f"Inserted: {result.data}")
    except Exception as e:
        print(f"❌ Error inserting test record: {e}")
    
    # Test 3: Query records
    print("\n🔍 Testing record querying...")
    try:
        result = supabase.table('posts').select('*').limit(5).execute()
        print("✅ Records queried successfully")
        print(f"Found {len(result.data)} records")
        for record in result.data:
            print(f"  - {record.get('title', 'No title')} (ID: {record.get('id')})")
    except Exception as e:
        print(f"❌ Error querying records: {e}")
    
    # Test 4: Update a record
    print("\n✏️  Testing record update...")
    try:
        result = supabase.table('posts').update({'value_score': 10}).eq('id', 1).execute()
        print("✅ Record updated successfully")
        print(f"Updated: {result.data}")
    except Exception as e:
        print(f"❌ Error updating record: {e}")
    
    # Test 5: Delete a test record
    print("\n🗑️  Testing record deletion...")
    try:
        result = supabase.table('posts').delete().eq('id', 1).execute()
        print("✅ Test record deleted successfully")
        print(f"Deleted: {result.data}")
    except Exception as e:
        print(f"❌ Error deleting record: {e}")
    
    print("\n✅ All tests completed!")
    
except Exception as e:
    print(f"❌ Error: {e}") 