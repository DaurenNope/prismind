#!/usr/bin/env python3
"""
Setup Supabase Tables

This script creates the necessary tables in Supabase if they don't exist.
"""

import os
from supabase import create_client
from dotenv import load_dotenv

def setup_database():
    """Create necessary tables in Supabase if they don't exist."""
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Error: Missing Supabase URL or Service Role Key in .env file")
        return False
    
    print("🔗 Connecting to Supabase...")
    
    try:
        # Initialize the client
        supabase = create_client(url, key)
        
        # SQL to create the posts table
        create_table_sql = """
        -- Enable the UUID extension if not already enabled
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- Create the posts table if it doesn't exist
        CREATE TABLE IF NOT EXISTS public.posts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            post_id TEXT NOT NULL,
            title TEXT,
            content TEXT,
            url TEXT UNIQUE,
            platform TEXT,
            author TEXT,
            author_handle TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            summary TEXT,
            ai_summary TEXT,
            folder_category TEXT,
            category TEXT,
            subcategory TEXT,
            topic TEXT,
            content_type TEXT,
            post_type TEXT,
            media_urls TEXT,
            hashtags TEXT,
            mentions TEXT,
            upvote_ratio FLOAT,
            num_comments INTEGER,
            is_saved BOOLEAN DEFAULT TRUE,
            saved_at TIMESTAMPTZ,
            analyzed_at TIMESTAMPTZ,
            sentiment TEXT,
            key_concepts TEXT,
            tags TEXT,
            analysis_model TEXT,
            value_score FLOAT DEFAULT 0,
            smart_tags TEXT,
            is_deleted BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Create an index on post_id for faster lookups
        CREATE INDEX IF NOT EXISTS idx_posts_post_id ON public.posts (post_id);

        -- Create an index on url for faster lookups
        CREATE INDEX IF NOT EXISTS idx_posts_url ON public.posts (url);

        -- Enable RLS (Row Level Security)
        ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;

        -- Create or replace the update_updated_at_column function
        CREATE OR REPLACE FUNCTION public.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        -- Create the trigger if it doesn't exist
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_trigger
                WHERE tgname = 'update_posts_updated_at'
            ) THEN
                CREATE TRIGGER update_posts_updated_at
                BEFORE UPDATE ON public.posts
                FOR EACH ROW
                EXECUTE FUNCTION public.update_updated_at_column();
            END IF;
        END $$;
        """
        
        # Execute the SQL to create the table
        print("🔄 Creating tables and indexes...")
        result = supabase.rpc('execute_sql', {'query': create_table_sql}).execute()
        
        if hasattr(result, 'error') and result.error:
            print(f"❌ Error creating tables: {result.error}")
            return False
        
        print("✅ Successfully set up database tables")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up database: {str(e)}")
        return False

def main():
    """Main function to set up the database."""
    print("🚀 Starting Supabase database setup...")
    
    if setup_database():
        print("\n🎉 Database setup completed successfully!")
        print("You can now run the sync script to sync your local data with Supabase.")
    else:
        print("\n❌ Database setup failed. Please check the error messages above.")
        print("\nTroubleshooting steps:")
        print("1. Verify your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the .env file")
        print("2. Make sure your Supabase project is running")
        print("3. Check if your IP is allowed in the Supabase dashboard")
        print("4. Verify the service role key has the correct permissions")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
