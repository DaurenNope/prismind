"""
Indexer Agent for PrisMind - handles content indexing and vector storage.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.indexing.embedding_service import get_embedding_service
from src.core.indexing.vector_db_manager import get_vector_db_manager

logger = logging.getLogger(__name__)


class IndexerAgent:
    """Agent responsible for indexing content and managing vector embeddings."""
    
    def __init__(self):
        """Initialize the indexer agent."""
        self.embedding_service = get_embedding_service()
        self.vector_db = get_vector_db_manager()
        
        # Ensure the embeddings table exists
        self.vector_db.create_embeddings_table()
        
        logger.info("IndexerAgent initialized")
    
    def is_ready(self) -> bool:
        """
        Check if the indexer agent is ready to process content.
        
        Returns:
            bool: True if ready, False otherwise
        """
        # The agent can work even if some components are not available
        # (it will log warnings but continue processing)
        return True
    
    def index_content(self, post) -> bool:
        """
        Index a single piece of content.
        
        Args:
            post: SocialPost to index
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.debug(f"Indexing content from {post.author} on {post.platform}")
            
            # Convert post to dictionary
            post_data = post.to_dict()
            
            # Prepare content for embedding
            content_for_embedding = self.embedding_service.prepare_content_for_embedding(post_data)
            
            # Generate content hash
            content_hash = self.embedding_service.get_content_hash(content_for_embedding)
            
            # Generate embedding
            embedding = self.embedding_service.generate_embedding(content_for_embedding)
            
            if embedding is None:
                logger.warning(f"Failed to generate embedding for post {post.url}")
                return False
            
            # Store embedding in vector database
            success = self.vector_db.store_embedding(
                content_hash=content_hash,
                embedding=embedding,
                metadata={
                    "content": post.content,
                    "platform": post.platform,
                    "author": post.author,
                    "author_handle": getattr(post, 'author_handle', ''),
                    "url": post.url,
                    "created_at": post.created_at.isoformat() if hasattr(post.created_at, 'isoformat') else str(post.created_at),
                    "post_type": getattr(post, 'post_type', 'unknown')
                }
            )
            
            if success:
                logger.debug(f"Successfully indexed content: {content_hash[:8]}...")
            else:
                logger.error(f"Failed to store embedding in database: {content_hash[:8]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"Error indexing content: {e}")
            return False
    
    def index_content_batch(self, posts: List) -> Dict[str, int]:
        """
        Index a batch of content items.
        
        Args:
            posts: List of SocialPost objects to index
            
        Returns:
            Dictionary with statistics about the indexing process
        """
        stats = {
            "total": len(posts),
            "successful": 0,
            "failed": 0
        }
        
        logger.info(f"Indexing batch of {len(posts)} content items")
        
        for i, post in enumerate(posts):
            try:
                success = self.index_content(post)
                if success:
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1
                    
                # Log progress for larger batches
                if len(posts) > 10 and (i + 1) % 10 == 0:
                    logger.info(f"Indexed {i + 1}/{len(posts)} items")
                    
            except Exception as e:
                logger.error(f"Error indexing post {i}: {e}")
                stats["failed"] += 1
        
        logger.info(f"Batch indexing complete: {stats}")
        return stats
    
    def search_similar_content(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for content similar to the query.
        
        Args:
            query: Query text
            limit: Maximum number of results
            
        Returns:
            List of similar content items
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_service.generate_embedding(query)
            
            if query_embedding is None:
                logger.warning("Failed to generate embedding for query")
                return []
            
            # Search for similar content
            results = self.vector_db.search_similar_content(query_embedding, limit)
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar content: {e}")
            return []


# Singleton instance
_indexer_agent: Optional[IndexerAgent] = None


def get_indexer_agent() -> IndexerAgent:
    """
    Get singleton instance of IndexerAgent.
    
    Returns:
        IndexerAgent: Singleton instance
    """
    global _indexer_agent
    if _indexer_agent is None:
        _indexer_agent = IndexerAgent()
    return _indexer_agent