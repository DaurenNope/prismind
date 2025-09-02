#!/usr/bin/env python3
"""
Create all tables for different content purposes
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not supabase_url or not supabase_key:
    print("❌ Missing Supabase credentials")
    exit(1)

try:
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("🔧 Creating tables for different content purposes...")
    
    # 1. Programming/Work Table
    programming_sql = """
    CREATE TABLE IF NOT EXISTS public.programming_posts (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        platform TEXT,
        author TEXT,
        author_handle TEXT,
        url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        summary TEXT,
        value_score INTEGER DEFAULT 0,
        smart_tags TEXT,
        ai_summary TEXT,
        folder_category TEXT,
        category TEXT,
        -- Programming specific fields
        language TEXT,
        framework TEXT,
        difficulty TEXT,
        code_snippets TEXT,
        tools_mentioned TEXT,
        implementation_status TEXT DEFAULT 'not_started'
    );
    
    ALTER TABLE public.programming_posts ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Allow all operations on programming_posts" ON public.programming_posts FOR ALL USING (true);
    
    CREATE INDEX IF NOT EXISTS idx_programming_language ON public.programming_posts(language);
    CREATE INDEX IF NOT EXISTS idx_programming_framework ON public.programming_posts(framework);
    CREATE INDEX IF NOT EXISTS idx_programming_difficulty ON public.programming_posts(difficulty);
    """
    
    # 2. Research (Evaluation) Table
    research_sql = """
    CREATE TABLE IF NOT EXISTS public.research_posts (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        platform TEXT,
        author TEXT,
        author_handle TEXT,
        url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        summary TEXT,
        value_score INTEGER DEFAULT 0,
        smart_tags TEXT,
        ai_summary TEXT,
        folder_category TEXT,
        category TEXT,
        -- Research specific fields
        research_topic TEXT,
        credibility_score INTEGER DEFAULT 0,
        fact_check_status TEXT DEFAULT 'pending',
        ai_evaluation TEXT,
        sources_cited TEXT,
        research_notes TEXT,
        evaluation_date TIMESTAMP WITH TIME ZONE
    );
    
    ALTER TABLE public.research_posts ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Allow all operations on research_posts" ON public.research_posts FOR ALL USING (true);
    
    CREATE INDEX IF NOT EXISTS idx_research_topic ON public.research_posts(research_topic);
    CREATE INDEX IF NOT EXISTS idx_research_credibility ON public.research_posts(credibility_score);
    CREATE INDEX IF NOT EXISTS idx_research_fact_check ON public.research_posts(fact_check_status);
    """
    
    # 3. Copywriting (Content Creation) Table
    copywriting_sql = """
    CREATE TABLE IF NOT EXISTS public.copywriting_posts (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        platform TEXT,
        author TEXT,
        author_handle TEXT,
        url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        summary TEXT,
        value_score INTEGER DEFAULT 0,
        smart_tags TEXT,
        ai_summary TEXT,
        folder_category TEXT,
        category TEXT,
        -- Copywriting specific fields
        content_type TEXT, -- 'social_media', 'blog', 'insight', 'rant', 'idea'
        target_platform TEXT, -- 'twitter', 'linkedin', 'instagram', etc.
        rewrite_instructions TEXT,
        tone TEXT, -- 'casual', 'professional', 'humorous', etc.
        call_to_action TEXT,
        hashtags TEXT,
        publish_status TEXT DEFAULT 'draft'
    );
    
    ALTER TABLE public.copywriting_posts ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Allow all operations on copywriting_posts" ON public.copywriting_posts FOR ALL USING (true);
    
    CREATE INDEX IF NOT EXISTS idx_copywriting_content_type ON public.copywriting_posts(content_type);
    CREATE INDEX IF NOT EXISTS idx_copywriting_target_platform ON public.copywriting_posts(target_platform);
    CREATE INDEX IF NOT EXISTS idx_copywriting_publish_status ON public.copywriting_posts(publish_status);
    """
    
    # Execute SQL using REST API
    import requests
    
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json'
    }
    
    tables_to_create = [
        ("programming_posts", programming_sql),
        ("research_posts", research_sql),
        ("copywriting_posts", copywriting_sql)
    ]
    
    for table_name, sql in tables_to_create:
        print(f"\n📋 Creating {table_name}...")
        
        # Try to execute SQL using the REST API
        response = requests.post(
            f"{supabase_url}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={'sql': sql}
        )
        
        if response.status_code == 200:
            print(f"✅ {table_name} created successfully!")
        else:
            print(f"❌ Error creating {table_name}: {response.status_code} - {response.text}")
            print(f"Please create {table_name} manually in the Supabase dashboard")
            print("SQL to run:")
            print(sql)
    
    print("\n✅ All tables created!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Please create the tables manually in the Supabase dashboard") 