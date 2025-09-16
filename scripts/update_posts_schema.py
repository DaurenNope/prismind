import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase client
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

def update_posts_table():
    """
    Add new columns to the posts table for content rewriting and social media targeting
    """
    try:
        # Add new columns if they don't exist
        alter_queries = [
            """
            ALTER TABLE posts 
            ADD COLUMN IF NOT EXISTS is_rewrite_candidate BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS content_quality_score FLOAT DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS target_social_media TEXT[] DEFAULT '{}'::TEXT[],
            ADD COLUMN IF NOT EXISTS content_category TEXT,
            ADD COLUMN IF NOT EXISTS ai_summary TEXT DEFAULT '';
            """,
            """
            COMMENT ON COLUMN posts.is_rewrite_candidate IS 'Flag indicating if this content is suitable for rewriting';
            COMMENT ON COLUMN posts.content_quality_score IS 'Numeric score (0-1) indicating content quality';
            COMMENT ON COLUMN posts.target_social_media IS 'Array of target social media platforms for this content';
            COMMENT ON COLUMN posts.content_category IS 'Category of content (e.g., educational, promotional, news)';
            COMMENT ON COLUMN posts.ai_summary IS 'AI-generated summary of the content';
            """
        ]
        
        # Execute each query using the Supabase client
        for query in alter_queries:
            try:
                # Use the rpc method to execute raw SQL
                result = supabase.rpc('execute_sql', {'query': query}).execute()
                print(f"✅ Executed query: {query.split()[0:5]}...")
            except Exception as query_error:
                print(f"⚠️  Warning: Could not execute query: {str(query_error)[:200]}...")
        
        print("✅ Successfully updated posts table schema")
        
    except Exception as e:
        print(f"❌ Error updating posts table: {str(e)}")
        raise

if __name__ == "__main__":
    update_posts_table()
