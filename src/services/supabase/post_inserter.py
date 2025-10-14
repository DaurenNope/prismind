"""
Supabase Post Inserter for PrisMind
Handles post insertion and data mapping
"""

import uuid
from typing import Dict, Any
from datetime import datetime


class PostInserter:
    """Handles post insertion and data mapping"""
    
    def __init__(self, client, duplicate_checker):
        """Initialize with Supabase client and duplicate checker"""
        self.client = client
        self.duplicate_checker = duplicate_checker
        self.table_name = 'posts'
    
    def insert_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new post into Supabase
        
        Args:
            post_data: Dictionary containing post data
            
        Returns:
            Dict containing the inserted post data, or empty dict on error/duplicate
        """
        try:
            if not post_data:
                return {}
            
            # Ensure we have required fields
            if not post_data.get('title') and not post_data.get('content'):
                return {}
            
            # Check for duplicates before inserting
            content = post_data.get('content', '')
            author = post_data.get('author', '')
            platform = post_data.get('platform', '')
            url = post_data.get('url', '')
            
            if self.duplicate_checker.check_duplicate_post(content, author, platform, url=url):
                print(f"Duplicate detected: {author} - {content[:50]}...")
                return {}  # Return empty dict to indicate duplicate
            
            # Generate post_id from URL or create a unique one
            post_id = post_data.get('post_id')
            if not post_id and url:
                # Simple approach: use last part of URL as post_id
                post_id = url.split('/')[-1] if '/' in url else url
            elif not post_id:
                # Generate a simple unique ID
                post_id = str(uuid.uuid4())[:8]
            
            # Map fields to match the actual Supabase table schema
            mapped_data = self._map_post_data(post_data, post_id)
            # Ensure JSON-serializable values (convert datetimes to isoformat)
            for k, v in list(mapped_data.items()):
                if isinstance(v, datetime):
                    mapped_data[k] = v.isoformat()
            
            # Make the insert request using proper Supabase client API
            response = self.client.table(self.table_name).insert(mapped_data).execute()
            
            # Handle the response
            if response.data:
                return response.data[0] if isinstance(response.data, list) else response.data
            
            return {"success": True}
            
        except Exception as e:
            # Silent fail - local DB is primary, Supabase is optional sync
            error_msg = str(e)
            if 'row-level security' not in error_msg.lower():
                # Only log non-RLS errors (RLS means not configured, expected)
                print(f"Supabase insert failed: {error_msg[:100]}")
            return {}
    
    def _map_post_data(self, post_data: Dict[str, Any], post_id: str) -> Dict[str, Any]:
        """Map post data to Supabase schema"""
        
        # Helper to convert list to PostgreSQL array format
        def to_pg_array(value):
            if not value or value == []:
                return None
            if isinstance(value, list):
                # Escape quotes and wrap in array format
                items = [str(item).replace('"', '\\"') for item in value]
                return '{' + ','.join(f'"{item}"' for item in items) + '}'
            return value
        
        # Extract author_handle from various possible fields
        author_handle = (
            post_data.get('username') or 
            post_data.get('author_handle') or 
            post_data.get('author', '').split()[0]  # Fallback: use first word of author
        )
        
        mapped_data = {
            'post_id': post_id,
            'title': post_data.get('title') or post_data.get('content', '')[:100] or '',  # Use content preview if no title
            'content': post_data.get('content') or '',
            'url': post_data.get('url') or '',
            'platform': post_data.get('platform') or '',
            'author': post_data.get('author') or '',
            'author_handle': author_handle,
            'created_at': post_data.get('created_at', datetime.now().isoformat()),
            
            # Use actual data from post, with fallbacks
            'post_type': post_data.get('post_type') or 'post',
            'content_type': post_data.get('content_type') or 'text',
            'is_saved': post_data.get('is_saved', True),
            'is_deleted': post_data.get('deleted', False) or post_data.get('is_deleted', False),
            'is_rewrite_candidate': post_data.get('is_rewrite_candidate', False),
            'is_time_sensitive': post_data.get('is_time_sensitive', False),
            
            # Convert arrays properly
            'media_urls': to_pg_array(post_data.get('media_urls')),
            'hashtags': to_pg_array(post_data.get('hashtags')),
            'mentions': to_pg_array(post_data.get('mentions')),
            'smart_tags': to_pg_array(post_data.get('smart_tags')),
            'target_social_media': to_pg_array(post_data.get('target_social_media')),
        }
        
        # Add optional fields if provided (don't override with None)
        optional_fields = [
            'category', 'subcategory', 'topic', 'summary', 'ai_summary',
            'sentiment', 'value_score', 'content_quality_score',
            'folder_category', 'saved_at', 'analyzed_at', 'key_concepts', 
            'tags', 'analysis_model', 'num_comments', 'upvote_ratio',
            'time_sensitivity_reason', 'embedding_model', 'language'
        ]
        
        for field in optional_fields:
            value = post_data.get(field)
            if value is not None and value != '':
                # Convert lists to PG arrays
                if isinstance(value, list):
                    mapped_data[field] = to_pg_array(value)
                else:
                    mapped_data[field] = value
        
        # Handle embedding vector specially (it's a list of floats, not a PG array)
        if 'embedding' in post_data and post_data['embedding']:
            # Embedding is already a list of floats, keep as-is for pgvector
            mapped_data['embedding'] = post_data['embedding']
        
        # Filter out any fields that analyzer produces but Supabase schema doesn't have
        # These are useful internally but not stored: action_items, actionable_items, 
        # learning_value, practical_applications, follow_up_research, quality_indicators,
        # related_skills, why_valuable, complexity_level, time_to_consume, confidence_score,
        # sentiment_scores, ai_service, intelligent_value_score, actionable_insights,
        # learning_recommendations, suggested_tags, analysis_version, topics (use topic instead)
        fields_to_remove = [
            'action_items', 'actionable_items', 'learning_value', 'practical_applications',
            'follow_up_research', 'quality_indicators', 'related_skills', 'why_valuable',
            'complexity_level', 'time_to_consume', 'confidence_score', 'sentiment_scores',
            'ai_service', 'intelligent_value_score', 'actionable_insights',
            'learning_recommendations', 'suggested_tags', 'analysis_version', 'topics',
            'username'  # Use author_handle instead
        ]
        for field in fields_to_remove:
            mapped_data.pop(field, None)
        
        # Handle engagement separately (it's a dict that might need JSON)
        if 'engagement' in post_data and post_data['engagement']:
            engagement = post_data['engagement']
            if isinstance(engagement, dict):
                # Extract specific engagement metrics if available
                mapped_data['num_comments'] = engagement.get('comments') or engagement.get('num_comments')
                mapped_data['upvote_ratio'] = engagement.get('upvote_ratio')
        
        return mapped_data
    
    def add_post(self, post_data: Dict[str, Any]) -> bool:
        """
        Add a new post to Supabase (compatibility method)
        
        Args:
            post_data: Dictionary containing post data
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.insert_post(post_data)
        return bool(result)


