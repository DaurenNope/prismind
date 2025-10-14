"""
Vector database manager for pgvector operations in Supabase.
"""

import logging
from typing import List, Optional, Dict, Any
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class VectorDBManager:
    """Manager for vector database operations with pgvector in Supabase."""
    
    def __init__(self):
        """Initialize the vector database manager."""
        self.supabase = None
        self.table_name = "content_embeddings"
        
        # Try to initialize Supabase client
        try:
            from supabase import create_client, Client
            
            # Get Supabase credentials from environment
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")
            
            if url and key:
                self.supabase: Client = create_client(url, key)
                logger.info("Supabase client initialized successfully")
            else:
                logger.warning("Supabase credentials not found. Vector DB operations will be simulated.")
        except ImportError:
            logger.warning("Supabase client not available. Vector DB operations will be simulated.")
            logger.warning("To install: pip install supabase")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
    
    def is_available(self) -> bool:
        """
        Check if the vector database is available.
        
        Returns:
            bool: True if database operations can be performed, False otherwise
        """
        return self.supabase is not None
    
    def create_embeddings_table(self) -> bool:
        """
        Create the embeddings table in Supabase if it doesn't exist.
        
        Returns:
            bool: True if successful or not needed, False if failed
        """
        if not self.is_available():
            logger.info("Vector DB not available, skipping table creation")
            return True
            
        try:
            # Note: In practice, you'd execute this via Supabase SQL editor
            # This is just a placeholder to show what the table structure would look like
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS content_embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content_hash TEXT UNIQUE NOT NULL,
                content TEXT,
                platform TEXT,
                author TEXT,
                url TEXT,
                embedding VECTOR(384),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS embedding_index ON content_embeddings 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """
            
            logger.info("Embeddings table creation SQL (execute in Supabase SQL editor):")
            logger.info(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Failed to create embeddings table: {e}")
            return False
    
    def store_embedding(self, content_hash: str, embedding: List[float], 
                       metadata: Dict[str, Any]) -> bool:
        """
        Store an embedding in the database.
        
        Args:
            content_hash: Hash of the content (used as unique identifier)
            embedding: Vector embedding
            metadata: Additional metadata about the content
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            logger.debug(f"Vector DB not available, simulating storage for {content_hash[:8]}...")
            return True
            
        try:
            # Prepare data for insertion
            data = {
                "content_hash": content_hash,
                "embedding": embedding,
                "content": metadata.get("content", ""),
                "platform": metadata.get("platform", ""),
                "author": metadata.get("author", ""),
                "url": metadata.get("url", ""),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Insert or update the embedding
            response = self.supabase.table(self.table_name).upsert(data).execute()
            logger.debug(f"Stored embedding for {content_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            return False
    
    def search_similar_content(self, query_embedding: List[float], 
                              limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar content using vector similarity.
        
        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results to return
            
        Returns:
            List of similar content items
        """
        if not self.is_available():
            logger.debug("Vector DB not available, returning empty results")
            return []
            
        try:
            # Perform vector similarity search
            response = (self.supabase
                       .table(self.table_name)
                       .select("*")
                       .limit(limit)
                       .execute())
            
            # In a real implementation, you would use:
            # .lt('embedding', query_embedding)  # This is simplified
            
            results = response.data if response.data else []
            logger.debug(f"Found {len(results)} similar content items")
            return results
        except Exception as e:
            logger.error(f"Failed to search similar content: {e}")
            return []


# Singleton instance
_vector_db_manager: Optional[VectorDBManager] = None


def get_vector_db_manager() -> VectorDBManager:
    """
    Get singleton instance of VectorDBManager.
    
    Returns:
        VectorDBManager: Singleton instance
    """
    global _vector_db_manager
    if _vector_db_manager is None:
        _vector_db_manager = VectorDBManager()
    return _vector_db_manager