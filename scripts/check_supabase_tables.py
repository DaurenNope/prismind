#!/usr/bin/env python3
"""
Check Supabase Connection and List Tables
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Error: Missing Supabase URL or Service Role Key in .env file")
        return
    
    print(f"🔗 Connecting to Supabase at {url}")
    
    try:
        # Initialize the client
        supabase: Client = create_client(url, key)
        
        # Test connection by getting the database version
        response = supabase.rpc('version').execute()
        
        if hasattr(response, 'error') and response.error:
            print(f"❌ Error connecting to Supabase: {response.error}")
            return
        
        print("✅ Successfully connected to Supabase")
        
        # Try to list all tables (this is a common way to check available tables)
        try:
            # This is a common way to list tables in Postgres via Supabase
            result = supabase.table('pg_tables') \
                        .select('tablename') \
                        .eq('schemaname', 'public') \
                        .execute()
            
            if hasattr(result, 'data') and result.data:
                print("\n📋 Available tables in your Supabase database:")
                for table in result.data:
                    print(f"- {table['tablename']}")
            else:
                print("\nℹ️ No tables found in the public schema")
                
        except Exception as e:
            print(f"\n⚠️ Could not list tables. You might not have permission or the schema might be empty.")
            print(f"Error details: {str(e)}")
        
        # Check if there are any tables using a different method
        try:
            # Try to get the first row from the 'posts' table (if it exists)
            result = supabase.table('posts').select('*').limit(1).execute()
            if hasattr(result, 'data') and result.data:
                print("\n✅ 'posts' table exists and contains data")
                print("\nExample post:", result.data[0])
            else:
                print("\nℹ️ 'posts' table either doesn't exist or is empty")
        except Exception as e:
            print(f"\n❌ Error accessing 'posts' table: {str(e)}")
        
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Verify your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the .env file")
        print("2. Make sure your Supabase project is running")
        print("3. Check if your IP is allowed in the Supabase dashboard")
        print("4. Verify the service role key has the correct permissions")

if __name__ == "__main__":
    main()
