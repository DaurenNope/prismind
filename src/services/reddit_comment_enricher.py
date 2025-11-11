"""
Reddit Comment Enricher

Extracts and summarizes valuable comments from Reddit posts to enrich rewriting.
"""

import logging
from typing import List, Dict, Any, Optional
from src.storage.db import get_storage

logger = logging.getLogger(__name__)


class RedditCommentEnricher:
    """
    Extract and summarize Reddit comments to add context to posts.

    Reddit discussions often contain valuable insights that aren't in the original post.
    This enricher extracts top comments and identifies key discussion themes.
    """

    def __init__(self):
        self.db = get_storage()
        logger.info("✅ Initialized RedditCommentEnricher")

    def extract_top_comments(
        self,
        post_id: str,
        min_score: int = 10,
        max_comments: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract top comments for a Reddit post

        Args:
            post_id: Reddit post ID
            min_score: Minimum upvote score for comments
            max_comments: Maximum number of comments to extract

        Returns:
            List of comment dicts with author, content, score
        """
        # Query comments from database
        # Assuming we have a comments table or comments are stored in posts table
        query = """
        SELECT
            comment_id,
            author,
            content,
            score,
            created_at
        FROM reddit_comments
        WHERE post_id = %s
            AND score >= %s
            AND is_deleted = FALSE
        ORDER BY score DESC
        LIMIT %s
        """

        try:
            comments = self.db.fetch_all(query, (post_id, min_score, max_comments))

            logger.info(f"📝 Extracted {len(comments)} top comments for post {post_id}")

            return comments

        except Exception as e:
            # If comments table doesn't exist or query fails, return empty
            logger.warning(f"Could not extract comments: {e}")
            return []

    def summarize_comments(
        self,
        comments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Summarize comments to extract key insights

        Args:
            comments: List of comment dicts

        Returns:
            Dict with:
            - top_insights: List of key insights
            - sentiment: Overall sentiment (positive/mixed/critical)
            - themes: Discussion themes
        """
        if not comments:
            return {
                'top_insights': [],
                'sentiment': 'neutral',
                'themes': []
            }

        # Extract insights (simple version - can be enhanced with LLM)
        insights = []
        for comment in comments[:3]:  # Top 3 comments
            content = comment.get('content', '')
            author = comment.get('author', 'Unknown')
            score = comment.get('score', 0)

            # Simple insight: first sentence + score
            first_sentence = content.split('.')[0][:150]
            insights.append({
                'content': first_sentence,
                'author': author,
                'score': score
            })

        # Analyze sentiment (simple keyword-based)
        sentiment = self._analyze_sentiment(comments)

        # Extract themes (simple keyword extraction)
        themes = self._extract_themes(comments)

        return {
            'top_insights': insights,
            'sentiment': sentiment,
            'themes': themes,
            'total_comments': len(comments)
        }

    def _analyze_sentiment(self, comments: List[Dict[str, Any]]) -> str:
        """
        Analyze overall sentiment from comments

        Args:
            comments: List of comment dicts

        Returns:
            'positive', 'mixed', or 'critical'
        """
        positive_keywords = ['great', 'amazing', 'love', 'excellent', 'perfect', 'awesome', 'helpful']
        negative_keywords = ['bad', 'terrible', 'hate', 'sucks', 'awful', 'useless', 'disappointing']

        positive_count = 0
        negative_count = 0

        for comment in comments:
            content_lower = comment.get('content', '').lower()

            for keyword in positive_keywords:
                if keyword in content_lower:
                    positive_count += 1

            for keyword in negative_keywords:
                if keyword in content_lower:
                    negative_count += 1

        if positive_count > negative_count * 2:
            return 'positive'
        elif negative_count > positive_count * 2:
            return 'critical'
        else:
            return 'mixed'

    def _extract_themes(self, comments: List[Dict[str, Any]]) -> List[str]:
        """
        Extract discussion themes from comments

        Args:
            comments: List of comment dicts

        Returns:
            List of theme keywords
        """
        # Simple keyword frequency extraction
        word_freq = {}

        for comment in comments:
            content = comment.get('content', '').lower()
            words = content.split()

            for word in words:
                # Filter out common words and short words
                if len(word) > 4 and word.isalpha():
                    word_freq[word] = word_freq.get(word, 0) + 1

        # Get top 5 most frequent words as themes
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        themes = [word for word, freq in sorted_words[:5] if freq >= 2]

        return themes

    def enrich_post(
        self,
        post: Dict[str, Any],
        min_comment_score: int = 10,
        max_comments: int = 5
    ) -> Dict[str, Any]:
        """
        Enrich a Reddit post with comment context

        Args:
            post: Post dict from usable_posts
            min_comment_score: Minimum score for comments
            max_comments: Maximum comments to include

        Returns:
            Enriched post dict with comment_context field
        """
        platform = post.get('platform', '')

        if platform != 'reddit':
            logger.debug(f"Post {post.get('post_id')} is not from Reddit, skipping enrichment")
            return post

        post_id = post.get('post_id')

        # Extract comments
        comments = self.extract_top_comments(
            post_id=post_id,
            min_score=min_comment_score,
            max_comments=max_comments
        )

        if not comments:
            logger.debug(f"No comments found for post {post_id}")
            return post

        # Summarize comments
        summary = self.summarize_comments(comments)

        # Add to post
        enriched_post = post.copy()
        enriched_post['comment_context'] = {
            'has_comments': True,
            'top_insights': summary['top_insights'],
            'sentiment': summary['sentiment'],
            'themes': summary['themes'],
            'total_comments': summary['total_comments']
        }

        logger.info(f"✅ Enriched post {post_id} with {len(comments)} comments")

        return enriched_post

    def format_comment_context_for_prompt(
        self,
        comment_context: Dict[str, Any]
    ) -> str:
        """
        Format comment context for inclusion in rewrite prompt

        Args:
            comment_context: Comment context dict from enrich_post

        Returns:
            Formatted string for prompt
        """
        if not comment_context.get('has_comments'):
            return ""

        insights = comment_context.get('top_insights', [])
        sentiment = comment_context.get('sentiment', 'neutral')
        themes = comment_context.get('themes', [])

        formatted = "\n\nREDDIT DISCUSSION CONTEXT:\n"
        formatted += f"Community sentiment: {sentiment}\n"

        if insights:
            formatted += "\nTop community insights:\n"
            for i, insight in enumerate(insights[:3], 1):
                content = insight['content']
                score = insight['score']
                formatted += f"{i}. [{score} upvotes] {content}\n"

        if themes:
            formatted += f"\nKey discussion themes: {', '.join(themes)}\n"

        return formatted


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("="*80)
    print("REDDIT COMMENT ENRICHER - DEMO")
    print("="*80)

    enricher = RedditCommentEnricher()

    # Example post (mock data)
    sample_post = {
        'post_id': 'abc123',
        'platform': 'reddit',
        'content': 'I tested all popular AI IDEs...',
        'title': 'AI IDE Comparison',
        'category': 'tech_trend'
    }

    # Mock comments for demo
    mock_comments = [
        {
            'comment_id': '1',
            'author': 'user1',
            'content': 'Great analysis! I love Cursor too, the AI autocomplete is amazing.',
            'score': 45,
            'created_at': '2025-11-09'
        },
        {
            'comment_id': '2',
            'author': 'user2',
            'content': 'Zed is excellent but still missing some features. Cursor is more mature.',
            'score': 32,
            'created_at': '2025-11-09'
        },
        {
            'comment_id': '3',
            'author': 'user3',
            'content': 'Have you tried GitHub Copilot in VSCode? Better integration in my experience.',
            'score': 28,
            'created_at': '2025-11-09'
        }
    ]

    print("\n📝 Sample Comments:")
    for comment in mock_comments:
        print(f"   [{comment['score']}↑] {comment['author']}: {comment['content'][:60]}...")

    # Summarize
    print("\n" + "="*80)
    print("Summarizing comments...")
    print("="*80)

    summary = enricher.summarize_comments(mock_comments)

    print(f"\n📊 Summary:")
    print(f"   Sentiment: {summary['sentiment']}")
    print(f"   Themes: {', '.join(summary['themes'])}")
    print(f"   Top insights: {len(summary['top_insights'])}")

    for insight in summary['top_insights']:
        print(f"     • [{insight['score']}↑] {insight['content']}")

    # Format for prompt
    print("\n" + "="*80)
    print("Formatted for prompt:")
    print("="*80)

    enriched_post = sample_post.copy()
    enriched_post['comment_context'] = {
        'has_comments': True,
        'top_insights': summary['top_insights'],
        'sentiment': summary['sentiment'],
        'themes': summary['themes'],
        'total_comments': len(mock_comments)
    }

    formatted = enricher.format_comment_context_for_prompt(enriched_post['comment_context'])
    print(formatted)

    print("="*80)
    print("✅ Demo complete!")
    print("="*80)
