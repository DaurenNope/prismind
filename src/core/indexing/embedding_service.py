"""
Embedding service for generating and managing vector embeddings using pgvector.
"""

import logging
from typing import List, Optional, Dict, Any
import hashlib
import json

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing content embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = None
        self.dimension = 384  # Default for all-MiniLM-L6-v2
        
        # Try to import and initialize the model
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Embedding model '{model_name}' loaded successfully with {self.dimension} dimensions")
        except ImportError:
            logger.warning("sentence-transformers not available. Embeddings will not be generated.")
            logger.warning("To install: pip install sentence-transformers")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
    
    def is_available(self) -> bool:
        """
        Check if the embedding service is available.
        
        Returns:
            bool: True if embeddings can be generated, False otherwise
        """
        return self.model is not None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector, or None if not available
        """
        if not self.is_available():
            logger.warning("Embedding service not available")
            return None
            
        if not text:
            return None
            
        try:
            embedding = self.model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text (alias for generate_embedding)"""
        return self.generate_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embeddings, with None for failed generations
        """
        if not self.is_available():
            logger.warning("Embedding service not available")
            return [None] * len(texts)
            
        try:
            embeddings = self.model.encode(texts)
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)
    
    def get_content_hash(self, content: str) -> str:
        """
        Generate a hash for content to use as a unique identifier.
        
        Args:
            content: Content to hash
            
        Returns:
            SHA-256 hash of the content
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def prepare_content_for_embedding(self, post_data: Dict[str, Any]) -> str:
        """
        Prepare content from a social post for embedding generation.
        
        Args:
            post_data: Dictionary containing post data
            
        Returns:
            String content prepared for embedding
        """
        # Combine important fields for embedding
        content_parts = []
        
        # Add main content
        if post_data.get('content'):
            content_parts.append(post_data['content'])
            
        # Add title if available
        if post_data.get('title'):
            content_parts.append(post_data['title'])
            
        # Add hashtags if available
        if post_data.get('hashtags'):
            if isinstance(post_data['hashtags'], list):
                hashtags = ' '.join([f"#{tag}" for tag in post_data['hashtags']])
                content_parts.append(hashtags)
            else:
                content_parts.append(str(post_data['hashtags']))
                
        # Add author for context
        if post_data.get('author'):
            content_parts.append(f"by {post_data['author']}")
            
        return ' '.join(content_parts)


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get singleton instance of EmbeddingService.
    
    Returns:
        EmbeddingService: Singleton instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service