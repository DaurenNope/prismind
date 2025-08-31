#!/usr/bin/env python3
"""
Check Supabase Database Schema
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def check_schema():
    """Check the current database schema"""
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print("🔍 Checking current database schema...")
        
        # Try to get table info
        try:
            # Get all posts to see the structure
            response = supabase.table('posts').select('*').limit(1).execute()
            print("✅ Posts table exists")
            
            if response.data:
                print("📊 Sample data structure:")
                for key, value in response.data[0].items():
                    print(f"  {key}: {type(value).__name__} = {value}")
            else:
                print("📊 Table is empty")
                
        except Exception as e:
            print(f"❌ Error accessing posts table: {e}")
            
        # Try to get table schema info
        try:
            # This might not work with PostgREST, but worth trying
            print("\n🔍 Attempting to get schema info...")
            # We'll try a simple insert to see what error we get
            test_data = {
                'id': 999999,
                'title': 'Schema Test',
                'platform': 'test'
            }
            
            response = supabase.table('posts').insert(test_data).execute()
            print("✅ Test insert successful")
            
        except Exception as e:
            print(f"❌ Test insert failed: {e}")
            
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")

if __name__ == "__main__":
    check_schema()
