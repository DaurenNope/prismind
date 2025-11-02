"""
Supabase Post Inserter for PrisMind
Handles post insertion and data mapping
"""

import uuid
from typing import Dict, Any
from datetime import datetime
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


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
            
            # FILTER OUT FIELDS THAT DON'T EXIST IN SUPABASE SCHEMA
            # Based on actual Supabase schema - only keep fields that exist
            supabase_schema_fields = {
                'id', 'post_id', 'title', 'content', 'url', 'platform', 'author', 'author_handle',
                'created_at', 'ai_summary', 'folder_category', 'category', 'subcategory', 'topic', 
                'content_type', 'post_type', 'media_urls', 'hashtags', 'mentions', 'is_saved',
                'analyzed_at', 'sentiment', 'key_concepts', 'tags', 'analysis_model', 'value_score',
                'smart_tags', 'is_deleted', 'updated_at', 'is_rewrite_candidate', 'content_quality_score',
                'embedding', 'embedding_model', 'language', 'collected_at'
            }
            
            # Create clean post data with ONLY fields that exist in Supabase schema
            clean_post_data = {k: v for k, v in post_data.items() if k in supabase_schema_fields}

            filtered_count = len(post_data) - len(clean_post_data)
            logger.debug(f"🧹 Schema filter: kept {len(clean_post_data)}/{len(post_data)} fields")
            if filtered_count > 0:
                filtered_fields = set(post_data.keys()) - supabase_schema_fields
                logger.debug(f"   Removed fields: {sorted(filtered_fields)}")
            
            # Ensure we have required fields
            if not clean_post_data.get('title') and not clean_post_data.get('content'):
                return {}
            
            # Check for duplicates before inserting
            content = clean_post_data.get('content', '')
            author = clean_post_data.get('author', '')
            platform = clean_post_data.get('platform', '')
            url = clean_post_data.get('url', '')
            
            if self.duplicate_checker.check_duplicate_post(content, author, platform, url=url):
                logger.info(f"Duplicate detected: {author} - {content[:50]}...")
                return {}  # Return empty dict to indicate duplicate
            
            # Generate post_id from URL or create a unique one
            post_id = clean_post_data.get('post_id')
            if not post_id and url:
                # Simple approach: use last part of URL as post_id
                post_id = url.split('/')[-1] if '/' in url else url
            elif not post_id:
                # Generate a simple unique ID
                post_id = str(uuid.uuid4())[:8]
            
            # Map fields to match the actual Supabase table schema
            mapped_data = self._map_post_data(clean_post_data, post_id)
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
                logger.error(f"Supabase insert failed: {error_msg[:100]}")
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
        
        # ESSENTIAL FIELDS ONLY - no more bloated schema issues!
        mapped_data = {
            'post_id': post_id,
            'content': post_data.get('content') or '',
            'url': post_data.get('url') or '',
            'platform': post_data.get('platform') or '',
            'author': post_data.get('author') or '',
            'author_handle': author_handle,
            'created_at': post_data.get('created_at', datetime.now().isoformat()),
            'language': post_data.get('language', 'en'),
            'is_saved': post_data.get('is_saved', True),
        }
        
        # Add analysis fields that exist in Supabase schema
        analysis_fields_mapping = {
            'ai_summary': 'ai_summary',
            'value_score': 'value_score', 
            'quality_score': 'content_quality_score',  # Schema uses content_quality_score
            'sentiment': 'sentiment',
            'key_concepts': 'key_concepts',
            'tags': 'tags',
            'category': 'category',
            'analysis_model': 'analysis_model',
            'embedding': 'embedding',
            'embedding_model': 'embedding_model'
        }
        
        for source_field, target_field in analysis_fields_mapping.items():
            value = post_data.get(source_field)
            if value is not None and value != '':
                # Convert lists to PG arrays for array fields
                if target_field in ['key_concepts', 'tags'] and isinstance(value, list):
                    mapped_data[target_field] = to_pg_array(value)
                else:
                    mapped_data[target_field] = value
        
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


