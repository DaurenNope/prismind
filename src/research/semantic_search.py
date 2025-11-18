#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Semantic search module.
This module provides capabilities for semantic search using sentence transformers.
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Try to import sentence transformers
SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning(
        "Warning: sentence-transformers not available. Semantic search will be limited."
    )


@dataclass
class SearchResult:
    """Represents a search result with similarity score."""

    text: str
    similarity: float
    index: int


class SemanticSearchEngine:
    """Semantic search engine using sentence transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the semantic search engine.

        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = None
        self.documents = []
        self.embeddings = None

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                logger.error(f"Error loading sentence transformer model: {e}")
                # We can't modify the global here, so we'll just disable locally
        else:
            logger.warning(
                "Semantic search capabilities limited due to missing dependencies."
            )

    def add_documents(self, documents: List[str]):
        """
        Add documents to the search index.

        Args:
            documents: List of text documents to add
        """
        self.documents.extend(documents)

        if SENTENCE_TRANSFORMERS_AVAILABLE and self.model:
            try:
                # Generate embeddings for all documents
                self.embeddings = self.model.encode(self.documents)
            except Exception as e:
                logger.error(f"Error encoding documents: {e}")
                self.embeddings = None
        else:
            logger.warning(
                "Cannot add documents: sentence-transformers not available or model not loaded."
            )

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search for documents semantically similar to the query.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of SearchResult objects
        """
        if (
            not SENTENCE_TRANSFORMERS_AVAILABLE
            or self.model is None
            or self.embeddings is None
        ):
            # Fallback to simple keyword matching
            return self._keyword_search(query, top_k)

        try:
            # Encode the query
            query_embedding = self.model.encode([query])

            # Calculate cosine similarities
            similarities = np.dot(self.embeddings, query_embedding[0]) / (
                np.linalg.norm(self.embeddings, axis=1)
                * np.linalg.norm(query_embedding[0])
            )

            # Get top-k results
            top_indices = np.argsort(similarities)[::-1][:top_k]

            # Create search results
            results = []
            for i, idx in enumerate(top_indices):
                results.append(
                    SearchResult(
                        text=self.documents[idx],
                        similarity=float(similarities[idx]),
                        index=int(idx),
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Error during semantic search: {e}")
            # Fallback to keyword search
            return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> List[SearchResult]:
        """
        Simple keyword-based search as fallback.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of SearchResult objects
        """
        query_words = set(query.lower().split())
        results = []

        for i, doc in enumerate(self.documents):
            doc_words = set(doc.lower().split())
            # Simple Jaccard similarity
            intersection = len(query_words.intersection(doc_words))
            union = len(query_words.union(doc_words))
            similarity = intersection / union if union > 0 else 0

            results.append(SearchResult(text=doc, similarity=similarity, index=i))

        # Sort by similarity
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]


# Example usage
def main():
    """Example usage of the semantic search engine."""
    logger.info("Semantic Search Engine Demo")
    logger.info("=" * 30)

    # Create the search engine
    search_engine = SemanticSearchEngine()

    # Add some sample documents
    documents = [
        "Large language models have revolutionized natural language processing tasks.",
        "Transformers are a type of neural network architecture used in many language models.",
        "Machine learning algorithms can be trained to perform various tasks.",
        "Natural language processing involves teaching computers to understand human language.",
        "Deep learning models require large amounts of data for training.",
        "Artificial intelligence is a broad field that encompasses machine learning.",
        "Neural networks are inspired by the structure of the human brain.",
        "Computer vision is a subfield of artificial intelligence focused on image processing.",
    ]

    logger.info("Adding documents to search index...")
    search_engine.add_documents(documents)

    # Perform a search
    query = "language models and neural networks"
    logger.info(f"\nSearching for: {query}\n")

    results = search_engine.search(query, top_k=3)

    for i, result in enumerate(results, 1):
        logger.info(f"{i}. Similarity: {result.similarity:.4f}")
        logger.info(f"   Text: {result.text}\n")


if __name__ == "__main__":
    main()
