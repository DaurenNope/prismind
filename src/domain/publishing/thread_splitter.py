"""
Thread Splitter

Automatically splits long content into Twitter/X threads with smart sentence boundaries.
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ThreadSplitter:
    """
    Split long content into Twitter threads with smart sentence boundaries.

    Features:
    - Respects sentence boundaries
    - Auto-numbering (1/, 2/, 3/)
    - Validates each tweet length
    - Handles line breaks properly
    """

    def __init__(self, max_length: int = 280):
        """
        Initialize thread splitter

        Args:
            max_length: Maximum characters per tweet (default: 280 for Twitter)
        """
        self.max_length = max_length
        # Reserve space for numbering (e.g., "1/ " = 3 chars)
        self.numbering_overhead = 3

    def split_into_thread(
        self, content: str, platform: str = "twitter"
    ) -> Dict[str, Any]:
        """
        Split content into thread if needed

        Args:
            content: Text to potentially split
            platform: Platform (twitter, threads, etc.)

        Returns:
            Dict with:
            {
                'is_thread': bool,
                'tweets': List[str],
                'tweet_count': int,
                'max_tweet_length': int,
                'warnings': List[str]
            }
        """
        # Clean content
        content = content.strip()

        # Check if splitting is needed
        effective_max = self.max_length - self.numbering_overhead

        if len(content) <= self.max_length:
            # No splitting needed
            return {
                "is_thread": False,
                "tweets": [content],
                "tweet_count": 1,
                "max_tweet_length": len(content),
                "warnings": [],
            }

        # Split into sentences
        sentences = self._split_into_sentences(content)

        # Build tweets from sentences
        tweets = []
        current_tweet = ""
        warnings = []

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            # Check if this sentence alone exceeds limit
            if len(sentence) > effective_max:
                # Sentence too long, need to split it
                logger.warning(
                    f"⚠️ Sentence exceeds max length ({len(sentence)} chars), will split mid-sentence"
                )

                # If we have accumulated content, save it
                if current_tweet:
                    tweets.append(current_tweet.strip())
                    current_tweet = ""

                # Split the long sentence into chunks
                chunks = self._split_sentence_into_chunks(sentence, effective_max)

                # Add all but last chunk as complete tweets
                for chunk in chunks[:-1]:
                    tweets.append(chunk)

                # Start new tweet with last chunk
                current_tweet = chunks[-1]
                warnings.append(f"Tweet {len(tweets)} had to be split mid-sentence")
                continue

            # Try adding sentence to current tweet
            test_tweet = current_tweet + (" " if current_tweet else "") + sentence

            if len(test_tweet) <= effective_max:
                # Fits in current tweet
                current_tweet = test_tweet
            else:
                # Doesn't fit, save current and start new
                if current_tweet:
                    tweets.append(current_tweet.strip())
                current_tweet = sentence

        # Add final tweet
        if current_tweet:
            tweets.append(current_tweet.strip())

        # Add numbering
        numbered_tweets = []
        for i, tweet in enumerate(tweets, 1):
            numbered_tweet = f"{i}/ {tweet}"
            numbered_tweets.append(numbered_tweet)

        # Validate lengths
        max_tweet_length = max(len(t) for t in numbered_tweets)

        if max_tweet_length > self.max_length:
            warnings.append(
                f"Thread tweet exceeds {self.max_length} chars: {max_tweet_length} chars"
            )

        result = {
            "is_thread": True,
            "tweets": numbered_tweets,
            "tweet_count": len(numbered_tweets),
            "max_tweet_length": max_tweet_length,
            "warnings": warnings,
        }

        logger.info(
            f"✂️ Split content into {len(numbered_tweets)} tweets (max length: {max_tweet_length} chars)"
        )

        return result

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences, respecting common abbreviations

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Common abbreviations that shouldn't trigger sentence splits
        abbreviations = {
            "Mr.",
            "Mrs.",
            "Ms.",
            "Dr.",
            "Prof.",
            "Inc.",
            "Ltd.",
            "Corp.",
            "Co.",
            "etc.",
            "vs.",
            "e.g.",
            "i.e.",
            "U.S.",
            "U.K.",
        }

        # Temporarily replace abbreviations with placeholders
        temp_text = text
        placeholders = {}

        for i, abbr in enumerate(abbreviations):
            if abbr in temp_text:
                placeholder = f"__ABBR{i}__"
                placeholders[placeholder] = abbr
                temp_text = temp_text.replace(abbr, placeholder)

        # Split on sentence boundaries (. ! ?)
        # Pattern: punctuation followed by space and capital letter, or end of string
        pattern = r"([.!?]+)(?:\s+(?=[A-ZА-Я])|$)"

        parts = re.split(pattern, temp_text)

        # Reconstruct sentences (combine text with its punctuation)
        sentences = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and parts[i + 1] in ".!?":
                # Text + punctuation
                sentence = parts[i] + parts[i + 1]
                sentences.append(sentence)
                i += 2
            elif parts[i].strip():
                sentences.append(parts[i])
                i += 1
            else:
                i += 1

        # Restore abbreviations
        restored_sentences = []
        for sentence in sentences:
            for placeholder, abbr in placeholders.items():
                sentence = sentence.replace(placeholder, abbr)
            restored_sentences.append(sentence)

        return restored_sentences

    def _split_sentence_into_chunks(self, sentence: str, max_length: int) -> List[str]:
        """
        Split a long sentence into chunks at word boundaries

        Args:
            sentence: Long sentence to split
            max_length: Maximum length per chunk

        Returns:
            List of chunks
        """
        words = sentence.split()
        chunks = []
        current_chunk = ""

        for word in words:
            test_chunk = current_chunk + (" " if current_chunk else "") + word

            if len(test_chunk) <= max_length:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def validate_thread(self, tweets: List[str]) -> Dict[str, Any]:
        """
        Validate a thread meets requirements

        Args:
            tweets: List of tweet strings

        Returns:
            Dict with validation results
        """
        warnings = []

        max_length = max(len(t) for t in tweets) if tweets else 0

        if max_length > self.max_length:
            warnings.append(
                f"Thread tweet exceeds {self.max_length} chars: {max_length} chars"
            )

        # Check numbering consistency
        for i, tweet in enumerate(tweets, 1):
            expected_prefix = f"{i}/ "
            if not tweet.startswith(expected_prefix):
                warnings.append(
                    f"Tweet {i} missing correct numbering (expected '{expected_prefix}')"
                )

        return {
            "valid": len(warnings) == 0,
            "tweet_count": len(tweets),
            "max_length": max_length,
            "warnings": warnings,
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    splitter = ThreadSplitter(max_length=280)

    # Test 1: Short content (no split needed)
    logger.info("=" * 80)
    logger.info("TEST 1: Short content")
    logger.info("=" * 80)

    short_content = "This is a short tweet that doesn't need splitting."
    result = splitter.split_into_thread(short_content)

    logger.info(f"Is thread: {result['is_thread']}")
    logger.info(f"Tweets: {result['tweet_count']}")
    for tweet in result["tweets"]:
        logger.info(f"  - {tweet}")

    # Test 2: Long content (needs splitting)
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Long content with multiple sentences")
    logger.info("=" * 80)

    long_content = """
    OpenAI leaked letter reveals federal guarantee request from October 27.
    Sam Altman's public statements contradicted this timeline.
    The company raised $6.6B in funding and projects 200% revenue growth.
    This raises serious questions about transparency in AI development.
    Government oversight may need to increase significantly.
    """

    result = splitter.split_into_thread(long_content.strip())

    logger.info(f"Is thread: {result['is_thread']}")
    logger.info(f"Tweets: {result['tweet_count']}")
    logger.info(f"Max length: {result['max_tweet_length']} chars")
    logger.warning(f"Warnings: {result['warnings']}")
    logger.info("\nThread:")
    for tweet in result["tweets"]:
        logger.info(f"  {tweet} ({len(tweet)} chars)")

    # Test 3: Very long single sentence
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Very long single sentence")
    logger.info("=" * 80)

    very_long = "This is an extremely long sentence that goes on and on and on without any natural breaking points and will definitely exceed the maximum tweet length limit so we need to split it intelligently at word boundaries while maintaining readability and coherence throughout the entire thread."

    result = splitter.split_into_thread(very_long)

    logger.info(f"Tweets: {result['tweet_count']}")
    logger.warning(f"Warnings: {result['warnings']}")
    logger.info("\nThread:")
    for tweet in result["tweets"]:
        logger.info(f"  {tweet} ({len(tweet)} chars)")
