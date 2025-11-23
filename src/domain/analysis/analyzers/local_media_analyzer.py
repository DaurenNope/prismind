#!/usr/bin/env python3
"""
Local Media Analyzer for Social Posts - Modular Implementation
Uses OCR + Local AI to analyze images and enhance post value
"""

import logging
from typing import Dict, List, Optional

from .media_ai_analyzer import MediaAIAnalyzer
from .media_ocr_analyzer import MediaOCRAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalMediaAnalyzer:
    """Analyzes media content in social posts using OCR and AI"""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ocr_analyzer = MediaOCRAnalyzer()
        self.ai_analyzer = MediaAIAnalyzer(ollama_url)

    def analyze_post_media(self, post: Dict) -> Dict:
        """Analyze all media in a post and return enhanced post data"""
        try:
            media_urls = post.get("media_urls", [])
            if not media_urls:
                return post

            logger.info(
                f"Analyzing {len(media_urls)} media items for post {post.get('id', 'unknown')}"
            )

            # Analyze each media item
            media_analysis = []
            total_value_boost = 0

            for i, media_url in enumerate(media_urls):
                media_id = f"{post.get('id', 'unknown')}_{i}"
                analysis = self.ocr_analyzer.analyze_single_media(media_url, media_id)

                if analysis:
                    # Enhance with AI analysis if text was found
                    if analysis.get("text_content"):
                        ai_analysis = self.ai_analyzer.analyze_text_with_ai(
                            analysis["text_content"]
                        )
                        analysis.update(ai_analysis)

                    # Calculate value boost
                    value_boost = self.ai_analyzer.calculate_value_boost(analysis)
                    analysis["value_boost"] = value_boost
                    total_value_boost += value_boost

                    media_analysis.append(analysis)

            # Enhance post with media insights
            enhanced_post = post.copy()
            enhanced_post["media_analysis"] = media_analysis
            enhanced_post["media_value_boost"] = total_value_boost

            # Add media insights to post content
            if media_analysis:
                insights = self.ai_analyzer.extract_media_insights(media_analysis)
                if insights:
                    enhanced_post["media_insights"] = insights

            # Update value score if it exists
            if "value_score" in enhanced_post:
                enhanced_post["value_score"] = min(
                    1.0, enhanced_post["value_score"] + (total_value_boost / 100.0)
                )

            logger.info(f"Media analysis complete. Value boost: +{total_value_boost}")
            return enhanced_post

        except Exception as e:
            logger.error(f"Error analyzing post media: {e}")
            return post

    def batch_analyze_posts(self, posts: List[Dict]) -> List[Dict]:
        """Analyze media for multiple posts"""
        enhanced_posts = []

        for post in posts:
            try:
                enhanced_post = self.analyze_post_media(post)
                enhanced_posts.append(enhanced_post)
            except Exception as e:
                logger.error(f"Error analyzing post {post.get('id', 'unknown')}: {e}")
                enhanced_posts.append(post)  # Return original post if analysis fails

        return enhanced_posts

    def is_available(self) -> bool:
        """Check if media analysis is available"""
        return self.ocr_analyzer.is_available()

    def get_capabilities(self) -> Dict[str, bool]:
        """Get available capabilities"""
        return self.ocr_analyzer.get_capabilities()


def main():
    """Test the media analyzer"""
    analyzer = LocalMediaAnalyzer()

    # Test post with media
    test_post = {
        "id": "test_123",
        "content": "Check out this cool image!",
        "media_urls": ["https://example.com/image.jpg"],
        "value_score": 0.7,
    }

    logger.info("Testing media analyzer...")
    logger.info(f"Available: {analyzer.is_available()}")
    logger.info(f"Capabilities: {analyzer.get_capabilities()}")

    if analyzer.is_available():
        result = analyzer.analyze_post_media(test_post)
        logger.info(f"Enhanced post: {result}")
    else:
        logger.warning("Media analysis not available - missing dependencies")


if __name__ == "__main__":
    main()
