#!/usr/bin/env python3
"""
Semantic Search Engine for BEYONDLINES
Provides advanced semantic search capabilities using sentence transformers
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .semantic_encoder import SemanticEncoder

logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    """
    Semantic search engine using sentence transformers for content similarity
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize semantic search engine

        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.encoder = SemanticEncoder(model_name)
        self.search_history = []

    def is_available(self) -> bool:
        """Check if semantic search is available"""
        return self.encoder.is_available()

    def search_similar_content(
        self,
        query: str,
        contents: List[Dict[str, Any]],
        top_k: int = 10,
        min_similarity: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Search for content similar to the query

        Args:
            query: Search query
            contents: List of content dictionaries with 'text' field
            top_k: Number of top results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of content dictionaries with similarity scores
        """
        if not self.is_available():
            logger.warning("⚠️ Semantic search not available, returning empty results")
            return []

        try:
            # Encode query
            query_embedding = self.encoder.encode_text(query)
            if query_embedding is None:
                return []

            # Prepare content texts
            content_texts = []
            valid_contents = []

            for content in contents:
                text = content.get("text", "")
                if text and len(text.strip()) > 10:
                    content_texts.append(text)
                    valid_contents.append(content)

            if not content_texts:
                return []

            # Encode content
            content_embeddings = self.encoder.encode_batch(content_texts)
            if content_embeddings is None:
                return []

            # Calculate similarities
            similarities = self.encoder.calculate_similarity(
                query_embedding, content_embeddings
            )

            # Create results with similarity scores
            results = []
            for i, (content, similarity) in enumerate(
                zip(valid_contents, similarities)
            ):
                if similarity >= min_similarity:
                    result = content.copy()
                    result["similarity_score"] = float(similarity)
                    result["rank"] = i + 1
                    results.append(result)

            # Sort by similarity score
            results.sort(key=lambda x: x["similarity_score"], reverse=True)

            # Return top_k results
            top_results = results[:top_k]

            # Log search
            self.search_history.append(
                {
                    "query": query,
                    "results_count": len(top_results),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            logger.info(f"🔍 Semantic search: '{query}' -> {len(top_results)} results")
            return top_results

        except Exception as e:
            logger.error(f"❌ Error in semantic search: {e}")
            return []

    def find_related_topics(
        self, query: str, contents: List[Dict[str, Any]], top_k: int = 5
    ) -> List[str]:
        """
        Find related topics based on semantic similarity

        Args:
            query: Base query
            contents: List of content dictionaries
            top_k: Number of related topics to return

        Returns:
            List of related topic strings
        """
        if not self.is_available():
            return []

        try:
            # Get similar content
            similar_content = self.search_similar_content(
                query, contents, top_k=top_k * 2
            )

            # Extract topics/keywords from similar content
            topics = set()
            for content in similar_content:
                # Extract from title, tags, or categories
                title = content.get("title", "")
                tags = content.get("tags", [])
                categories = content.get("categories", [])

                if title:
                    topics.add(title.lower())

                if isinstance(tags, list):
                    topics.update([tag.lower() for tag in tags])

                if isinstance(categories, list):
                    topics.update([cat.lower() for cat in categories])

            # Return top topics
            return list(topics)[:top_k]

        except Exception as e:
            logger.error(f"❌ Error finding related topics: {e}")
            return []

    def cluster_content(
        self, contents: List[Dict[str, Any]], n_clusters: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Cluster content based on semantic similarity

        Args:
            contents: List of content dictionaries
            n_clusters: Number of clusters to create

        Returns:
            List of content dictionaries with cluster assignments
        """
        if not self.is_available():
            return contents

        try:
            from sklearn.cluster import KMeans

            # Prepare content texts
            content_texts = []
            valid_contents = []

            for content in contents:
                text = content.get("text", "")
                if text and len(text.strip()) > 10:
                    content_texts.append(text)
                    valid_contents.append(content)

            if len(content_texts) < n_clusters:
                # Not enough content for clustering
                for content in valid_contents:
                    content["cluster_id"] = 0
                return valid_contents

            # Encode content
            content_embeddings = self.encoder.encode_batch(content_texts)
            if content_embeddings is None:
                return valid_contents

            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(content_embeddings)

            # Add cluster assignments
            for i, content in enumerate(valid_contents):
                content["cluster_id"] = int(cluster_labels[i])

            logger.info(
                f"📊 Clustered {len(valid_contents)} items into {n_clusters} clusters"
            )
            return valid_contents

        except Exception as e:
            logger.error(f"❌ Error clustering content: {e}")
            return contents

    def get_content_summary(
        self, contents: List[Dict[str, Any]], max_items: int = 10
    ) -> Dict[str, Any]:
        """
        Get a summary of content collection

        Args:
            contents: List of content dictionaries
            max_items: Maximum number of items to include in summary

        Returns:
            Summary dictionary
        """
        try:
            if not contents:
                return {"total_items": 0, "summary": "No content available"}

            # Basic statistics
            total_items = len(contents)
            total_text_length = sum(
                len(content.get("text", "")) for content in contents
            )
            avg_text_length = total_text_length / total_items if total_items > 0 else 0

            # Extract common topics
            all_tags = []
            all_categories = []

            for content in contents:
                tags = content.get("tags", [])
                categories = content.get("categories", [])

                if isinstance(tags, list):
                    all_tags.extend(tags)
                if isinstance(categories, list):
                    all_categories.extend(categories)

            # Count tag frequency
            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Get top tags
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            # Sample content
            sample_content = contents[:max_items]

            summary = {
                "total_items": total_items,
                "total_text_length": total_text_length,
                "average_text_length": avg_text_length,
                "top_tags": top_tags,
                "sample_content": sample_content,
                "generated_at": datetime.now().isoformat(),
            }

            return summary

        except Exception as e:
            logger.error(f"❌ Error generating content summary: {e}")
            return {"error": str(e)}

    def get_search_history(self) -> List[Dict[str, Any]]:
        """Get search history"""
        return self.search_history.copy()

    def clear_search_history(self):
        """Clear search history"""
        self.search_history.clear()
        logger.info("🧹 Cleared search history")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.encoder.get_cache_stats()

    def clear_cache(self):
        """Clear the embedding cache"""
        self.encoder.clear_cache()
