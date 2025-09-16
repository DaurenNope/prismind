#!/usr/bin/env python3
"""Test Supabase connection and table structure."""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

def main():
    """Test Supabase connection and check posts table structure."""
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Error: Missing Supabase URL or Service Role Key in .env file")
        sys.exit(1)
    
    print("🔌 Connecting to Supabase...")
    
    try:
        # Initialize the client
        supabase = create_client(url, key)
        
        # Test connection by getting the first post
        print("\n🔍 Testing connection by fetching first post...")
        result = supabase.table('posts').select('*').limit(1).execute()
        
        if hasattr(result, 'data') and result.data:
            print("✅ Successfully connected to Supabase!")
            print("\n📋 First post data:")
            for key, value in result.data[0].items():
                print(f"- {key}: {value}")
            
            # Get column information from the first row
            print("\n📋 Posts table columns (inferred from first row):")
            for key in result.data[0].keys():
                print(f"- {key} ({type(result.data[0][key]).__name__})")
        else:
            print("ℹ️ No posts found in the database.")
            
            # Try to get table structure from information_schema
            print("\n🔍 Trying to get table structure...")
            try:
                # This is a raw SQL query that should work in most PostgreSQL databases
                query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'posts';
                """
                result = supabase.rpc('rpc', {'query': query}).execute()
                
                if hasattr(result, 'data') and result.data:
                    print("\n📋 Posts table structure:")
                    for col in result.data:
                        default = f"DEFAULT {col['column_default']}" if col['column_default'] else ''
                        print(f"- {col['column_name']} ({col['data_type']}) {'NOT NULL' if col['is_nullable'] == 'NO' else 'NULL'} {default}")
                else:
                    print("❌ Could not get table structure from information_schema")
            except Exception as e:
                print(f"❌ Error getting table structure: {e}")
        
        # Try to insert a test post
        print("\n🧪 Testing post insertion...")
        test_post = {
            'title': 'Test Post',
            'content': 'This is a test post to check Supabase connection.',
            'url': f'https://example.com/test-{os.urandom(8).hex()}',
            'platform': 'test',
            'author': 'test_user',
            'author_handle': 'test_user',
            'value_score': 0,
            'smart_tags': 'test,integration'
        }
        
        try:
            # First, delete any existing test posts
            supabase.table('posts').delete().eq('platform', 'test').execute()
            
            # Insert the test post
            result = supabase.table('posts').insert(test_post).execute()
            
            if hasattr(result, 'data') and result.data:
                print(f"✅ Successfully inserted test post with ID: {result.data[0]['id']}")
                
                # Try to retrieve the test post
                print("\n🔍 Retrieving the test post...")
                test_post_id = result.data[0]['id']
                retrieved = supabase.table('posts').select('*').eq('id', test_post_id).execute()
                
                if hasattr(retrieved, 'data') and retrieved.data:
                    print("✅ Successfully retrieved test post:")
                    for key, value in retrieved.data[0].items():
                        print(f"- {key}: {value}")
                else:
                    print("❌ Could not retrieve the test post")
            else:
                print(f"❌ Failed to insert test post: {result}")
        except Exception as e:
            print(f"❌ Error during test post insertion: {e}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
