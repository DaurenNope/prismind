#!/usr/bin/env python3
"""
Multi-Table Supabase Database Manager
Handles programming_posts, research_posts, and copywriting_posts
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import List, Dict, Any, Optional

class MultiTableManager:
    def __init__(self):
        load_dotenv()
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in .env file")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
    
    # ===== PROGRAMMING POSTS =====
    def insert_programming_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a programming/work post"""
        try:
            result = self.client.table('programming_posts').insert(post_data).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            print(f"❌ Error inserting programming post: {e}")
            return {}
    
    def get_programming_posts(self, language: Optional[str] = None, framework: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get programming posts with optional filtering"""
        try:
            query = self.client.table('programming_posts').select('*')
            
            if language:
                query = query.eq('language', language)
            if framework:
                query = query.eq('framework', framework)
            
            result = query.limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting programming posts: {e}")
            return []
    
    def get_programming_by_difficulty(self, difficulty: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get programming posts by difficulty level"""
        try:
            result = self.client.table('programming_posts').select('*').eq('difficulty', difficulty).limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting programming posts by difficulty: {e}")
            return []
    
    # ===== RESEARCH POSTS =====
    def insert_research_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a research/evaluation post"""
        try:
            result = self.client.table('research_posts').insert(post_data).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            print(f"❌ Error inserting research post: {e}")
            return {}
    
    def get_research_posts(self, topic: Optional[str] = None, fact_check_status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get research posts with optional filtering"""
        try:
            query = self.client.table('research_posts').select('*')
            
            if topic:
                query = query.eq('research_topic', topic)
            if fact_check_status:
                query = query.eq('fact_check_status', fact_check_status)
            
            result = query.limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting research posts: {e}")
            return []
    
    def get_high_credibility_research(self, min_score: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Get research posts with high credibility scores"""
        try:
            result = self.client.table('research_posts').select('*').gte('credibility_score', min_score).limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting high credibility research: {e}")
            return []
    
    # ===== COPYWRITING POSTS =====
    def insert_copywriting_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a copywriting/content creation post"""
        try:
            result = self.client.table('copywriting_posts').insert(post_data).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            print(f"❌ Error inserting copywriting post: {e}")
            return {}
    
    def get_copywriting_posts(self, content_type: Optional[str] = None, target_platform: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get copywriting posts with optional filtering"""
        try:
            query = self.client.table('copywriting_posts').select('*')
            
            if content_type:
                query = query.eq('content_type', content_type)
            if target_platform:
                query = query.eq('target_platform', target_platform)
            
            result = query.limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting copywriting posts: {e}")
            return []
    
    def get_draft_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get draft copywriting posts"""
        try:
            result = self.client.table('copywriting_posts').select('*').eq('publish_status', 'draft').limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting draft posts: {e}")
            return []
    
    # ===== UNIVERSAL METHODS =====
    def update_post(self, table_name: str, post_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a post in any table"""
        try:
            result = self.client.table(table_name).update(updates).eq('id', post_id).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            print(f"❌ Error updating post in {table_name}: {e}")
            return {}
    
    def delete_post(self, table_name: str, post_id: int) -> bool:
        """Delete a post from any table"""
        try:
            result = self.client.table(table_name).delete().eq('id', post_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"❌ Error deleting post from {table_name}: {e}")
            return False
    
    def search_all_tables(self, search_term: str, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search across all tables"""
        results = {}
        tables = ['programming_posts', 'research_posts', 'copywriting_posts']
        
        for table in tables:
            try:
                result = self.client.table(table).select('*').or_(
                    f'title.ilike.%{search_term}%,content.ilike.%{search_term}%'
                ).limit(limit).execute()
                results[table] = result.data
            except Exception as e:
                print(f"❌ Error searching {table}: {e}")
                results[table] = []
        
        return results

# Example usage
if __name__ == "__main__":
    try:
        db = MultiTableManager()
        
        # Test Programming Posts
        print("🔧 Testing Programming Posts...")
        programming_post = {
            'id': 1001,
            'title': 'React Hooks Tutorial',
            'content': 'Learn how to use React hooks effectively...',
            'platform': 'medium',
            'author': 'React Dev',
            'language': 'javascript',
            'framework': 'react',
            'difficulty': 'intermediate',
            'implementation_status': 'not_started'
        }
        
        inserted = db.insert_programming_post(programming_post)
        if inserted:
            print(f"✅ Inserted programming post: {inserted['title']}")
        
        # Test Research Posts
        print("\n🔬 Testing Research Posts...")
        research_post = {
            'id': 2001,
            'title': 'AI in Healthcare Study',
            'content': 'Recent study on AI applications in healthcare...',
            'platform': 'arxiv',
            'research_topic': 'healthcare',
            'credibility_score': 8,
            'fact_check_status': 'pending'
        }
        
        inserted = db.insert_research_post(research_post)
        if inserted:
            print(f"✅ Inserted research post: {inserted['title']}")
        
        # Test Copywriting Posts
        print("\n✍️  Testing Copywriting Posts...")
        copywriting_post = {
            'id': 3001,
            'title': 'Social Media Post Idea',
            'content': 'Great insight about productivity...',
            'platform': 'twitter',
            'content_type': 'social_media',
            'target_platform': 'twitter',
            'tone': 'casual',
            'publish_status': 'draft'
        }
        
        inserted = db.insert_copywriting_post(copywriting_post)
        if inserted:
            print(f"✅ Inserted copywriting post: {inserted['title']}")
        
        # Test getting posts
        print("\n📋 Getting posts from each table...")
        programming_posts = db.get_programming_posts(limit=3)
        research_posts = db.get_research_posts(limit=3)
        copywriting_posts = db.get_copywriting_posts(limit=3)
        
        print(f"Programming: {len(programming_posts)} posts")
        print(f"Research: {len(research_posts)} posts")
        print(f"Copywriting: {len(copywriting_posts)} posts")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}") 