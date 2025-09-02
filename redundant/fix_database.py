#!/usr/bin/env python3
"""
Database Schema Fix Script
Run this to fix the Supabase database schema for large Twitter post IDs
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def fix_database_schema():
    """Fix the database schema by recreating the table with BIGINT"""
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in environment variables")
        print("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print("🔧 Fixing database schema...")
        print("📝 This will recreate the posts table with BIGINT for id column")
        
        # Read the fix script
        with open('scripts/fix_database_schema.sql', 'r') as f:
            sql_script = f.read()
        
        # Execute the SQL script
        result = supabase.rpc('exec_sql', {'sql': sql_script}).execute()
        
        print("✅ Database schema fixed successfully!")
        print("✅ Posts table now uses BIGINT for id column")
        print("✅ Can now handle large Twitter post IDs")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        print("\n📋 Manual Instructions:")
        print("1. Go to your Supabase dashboard")
        print("2. Open the SQL Editor")
        print("3. Copy and paste the contents of scripts/fix_database_schema.sql")
        print("4. Run the SQL script")
        return False

if __name__ == "__main__":
    print("🚀 Database Schema Fix Tool")
    print("=" * 40)
    
    success = fix_database_schema()
    
    if success:
        print("\n🎉 Database is now ready for Twitter collection!")
        print("You can now run the app and collect posts without errors.")
    else:
        print("\n⚠️ Please fix the database schema manually using the instructions above.")
