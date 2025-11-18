#!/usr/bin/env python3
"""
Semantic Encoder for BEYONDLINES
Handles text encoding and similarity calculations using sentence transformers
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    SEMANTIC_AVAILABLE = True
except ImportError:
    logger.error(f"Error: {e}")
    SEMANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class SemanticEncoder:
    """Handles text encoding and similarity calculations"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize semantic encoder

        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = None
        self.embedding_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

        if SEMANTIC_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"✅ Loaded semantic model: {model_name}")
            except Exception as e:
                logger.error(f"❌ Failed to load semantic model: {e}")
                self.model = None
        else:
            logger.warning("⚠️ Semantic search dependencies not available")

    def is_available(self) -> bool:
        """Check if semantic encoding is available"""
        return SEMANTIC_AVAILABLE and self.model is not None

    def encode_text(self, text: str) -> Optional[np.ndarray]:
        """
        Encode a single text into semantic embedding

        Args:
            text: Text to encode

        Returns:
            Numpy array with embedding or None if failed
        """
        if not self.is_available():
            return None

        # Check cache first
        text_hash = hash(text)
        if text_hash in self.embedding_cache:
            self.cache_hits += 1
            return self.embedding_cache[text_hash]

        try:
            # Clean and prepare text
            cleaned_text = self._clean_text(text)
            if not cleaned_text:
                return None

            # Encode text
            embedding = self.model.encode(cleaned_text)

            # Cache the result
            self.embedding_cache[text_hash] = embedding
            self.cache_misses += 1

            return embedding

        except Exception as e:
            logger.error(f"❌ Error encoding text: {e}")
            return None

    def encode_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Encode multiple texts into semantic embeddings

        Args:
            texts: List of texts to encode

        Returns:
            Numpy array with embeddings or None if failed
        """
        if not self.is_available():
            return None

        try:
            # Clean texts
            cleaned_texts = [self._clean_text(text) for text in texts]
            cleaned_texts = [text for text in cleaned_texts if text]

            if not cleaned_texts:
                return None

            # Encode batch
            embeddings = self.model.encode(cleaned_texts)

            # Cache results
            for text, embedding in zip(cleaned_texts, embeddings):
                text_hash = hash(text)
                self.embedding_cache[text_hash] = embedding
                self.cache_misses += 1

            return embeddings

        except Exception as e:
            logger.error(f"❌ Error encoding batch: {e}")
            return None

    def calculate_similarity(
        self, query_embedding: np.ndarray, content_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calculate similarity between query and content embeddings

        Args:
            query_embedding: Query embedding
            content_embeddings: Content embeddings

        Returns:
            Array of similarity scores
        """
        try:
            # Reshape query embedding for cosine similarity
            query_reshaped = query_embedding.reshape(1, -1)

            # Calculate cosine similarity
            similarities = cosine_similarity(query_reshaped, content_embeddings)[0]

            return similarities

        except Exception as e:
            logger.error(f"❌ Error calculating similarity: {e}")
            return np.array([])

    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for encoding"""
        if not text:
            return ""

        # Basic cleaning
        text = text.strip()
        text = text.replace("\n", " ").replace("\r", " ")
        text = " ".join(text.split())  # Remove extra whitespace

        # Remove very short texts
        if len(text) < 10:
            return ""

        return text

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.embedding_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses)
            if (self.cache_hits + self.cache_misses) > 0
            else 0,
        }

    def clear_cache(self):
        """Clear the embedding cache"""
        self.embedding_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("🧹 Cleared semantic embedding cache")

    def get_cache_size(self) -> int:
        """Get current cache size"""
        return len(self.embedding_cache)
