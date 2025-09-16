#!/usr/bin/env python3
"""Check the Supabase posts table schema."""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

def main():
    """Check the Supabase posts table schema."""
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
        
        # Get the table structure from information_schema
        print("\n📋 Checking posts table structure...")
        
        # Try to get the table definition
        try:
            # This is a raw SQL query to get the table structure
            result = supabase.rpc('get_table_definition', {'table_name': 'posts'}).execute()
            print("Table definition:")
            print(result)
        except Exception as e:
            print(f"Could not get table definition via RPC: {e}")
        
        # Try to get the column information using a direct query
        print("\n📋 Checking posts table columns...")
        try:
            # This is a raw SQL query to get the table structure
            result = supabase.rpc('get_table_columns', {'table_name': 'posts'}).execute()
            if hasattr(result, 'data') and result.data:
                print("\n📋 Posts table columns:")
                for col in result.data:
                    print(f"- {col['name']} ({col['type']}) {'NOT NULL' if not col['is_nullable'] else 'NULL'}")
            else:
                print("❌ Could not get column information")
        except Exception as e:
            print(f"❌ Error getting column information: {e}")
            
            # Fallback to a simple query to just get the column names
            try:
                print("\nTrying to get column names with a simple query...")
                result = supabase.table('posts').select('*').limit(1).execute()
                if hasattr(result, 'data') and result.data and len(result.data) > 0:
                    print("\n📋 Posts table columns (inferred from first row):")
                    for key in result.data[0].keys():
                        print(f"- {key}")
            except Exception as e2:
                print(f"❌ Could not get column names: {e2}")
        
        # Try to get the primary key information
        print("\n🔑 Checking primary key constraints...")
        result = supabase.table('information_schema.table_constraints') \
            .select('*') \
            .eq('table_name', 'posts') \
            .eq('constraint_type', 'PRIMARY KEY') \
            .execute()
            
        if hasattr(result, 'data') and result.data:
            for constraint in result.data:
                print(f"Primary key constraint: {constraint['constraint_name']}")
                
                # Get the columns in the primary key
                cols = supabase.table('information_schema.key_column_usage') \
                    .select('column_name') \
                    .eq('constraint_name', constraint['constraint_name']) \
                    .execute()
                    
                if hasattr(cols, 'data') and cols.data:
                    print("  Columns:", ", ".join([col['column_name'] for col in cols.data]))
        else:
            print("❌ Could not get primary key information")
        
        # Check if there's a sequence for auto-increment
        print("\n🔍 Checking for sequences...")
        try:
            result = supabase.rpc('get_sequence_info', {'table_name': 'posts'}).execute()
            print("Sequence info:", result)
        except Exception as e:
            print(f"Could not get sequence info: {e}")
        
        # Try to get the default value for the id column
        print("\n🔍 Checking default values...")
        result = supabase.table('information_schema.columns') \
            .select('column_default') \
            .eq('table_name', 'posts') \
            .eq('column_name', 'id') \
            .execute()
            
        if hasattr(result, 'data') and result.data and len(result.data) > 0:
            print(f"Default value for id column: {result.data[0]['column_default']}")
        else:
            print("❌ Could not get default value for id column")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
