"""
Voice Consistency Validator

Validates that rewrites match the persona's voice by:
- Checking vocabulary similarity to persona examples
- Analyzing tone consistency
- Detecting off-brand language
- Ensuring style consistency
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import Counter
import re
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class VoiceValidator:
    """
    Validates voice consistency between rewrites and persona examples.

    Checks:
    1. Vocabulary similarity (word choice)
    2. Tone consistency (formal vs casual)
    3. Off-brand language detection
    4. Style patterns (sentence structure, punctuation)
    """

    def __init__(self):
        """Initialize the voice validator"""
        self.persona_profiles = self._load_persona_profiles()
        logger.info("✅ VoiceValidator initialized")

    def _load_persona_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load persona profiles with voice characteristics"""
        profiles = {}
        config_dir = Path(__file__).parent.parent.parent / "config" / "personas"

        for persona in ["qronoya", "aspandead", "claimzilla"]:
            persona_file = config_dir / f"{persona}.json"
            examples_file = config_dir / f"{persona}_examples.json"

            if persona_file.exists():
                try:
                    with open(persona_file, 'r', encoding='utf-8') as f:
                        persona_data = json.load(f)

                    # Load examples
                    examples = []
                    if examples_file.exists():
                        with open(examples_file, 'r', encoding='utf-8') as f:
                            examples_data = json.load(f)
                            examples = [
                                ex.get('content', '')
                                for ex in examples_data.get('examples', [])
                                if ex.get('content', '').strip()
                            ]

                    # Extract voice characteristics
                    profiles[persona] = {
                        'name': persona_data.get('name', persona),
                        'language': persona_data.get('language', 'en'),
                        'tone': persona_data.get('voice_tone', []),
                        'vocabulary': self._extract_vocabulary(examples),
                        'common_words': self._get_common_words(examples, top_n=100),
                        'sentence_patterns': self._analyze_sentence_patterns(examples),
                        'punctuation_style': self._analyze_punctuation(examples),
                        'examples': examples
                    }

                    logger.info(f"Loaded voice profile for {persona} ({len(examples)} examples)")

                except Exception as e:
                    logger.error(f"Error loading {persona} profile: {e}")
                    profiles[persona] = {}

        return profiles

    def _extract_vocabulary(self, texts: List[str]) -> Set[str]:
        """Extract vocabulary (unique words) from texts"""
        vocabulary = set()

        for text in texts:
            # Tokenize (split on whitespace and punctuation)
            words = re.findall(r'\b\w+\b', text.lower())
            vocabulary.update(words)

        return vocabulary

    def _get_common_words(self, texts: List[str], top_n: int = 100) -> List[Tuple[str, int]]:
        """Get most common words from texts"""
        word_counts = Counter()

        # Common stop words to exclude
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }

        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            # Filter out stop words and very short words
            words = [w for w in words if w not in stop_words and len(w) > 2]
            word_counts.update(words)

        return word_counts.most_common(top_n)

    def _analyze_sentence_patterns(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze sentence structure patterns"""
        sentence_lengths = []
        starts_with_question = 0
        starts_with_capital = 0
        total_sentences = 0

        for text in texts:
            # Split into sentences (rough approximation)
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            for sentence in sentences:
                total_sentences += 1
                sentence_lengths.append(len(sentence))

                if sentence.startswith('?') or sentence.lower().startswith(('what', 'why', 'how', 'when', 'where', 'who')):
                    starts_with_question += 1

                if sentence and sentence[0].isupper():
                    starts_with_capital += 1

        avg_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0

        return {
            'avg_sentence_length': avg_length,
            'question_rate': starts_with_question / total_sentences if total_sentences > 0 else 0,
            'capitalization_rate': starts_with_capital / total_sentences if total_sentences > 0 else 0
        }

    def _analyze_punctuation(self, texts: List[str]) -> Dict[str, float]:
        """Analyze punctuation usage patterns"""
        punctuation_counts = Counter()
        total_chars = 0

        for text in texts:
            total_chars += len(text)
            # Count each punctuation type
            punctuation_counts['!'] += text.count('!')
            punctuation_counts['?'] += text.count('?')
            punctuation_counts['.'] += text.count('.')
            punctuation_counts[','] += text.count(',')
            punctuation_counts['-'] += text.count(' - ')
            punctuation_counts['...'] += text.count('...')
            punctuation_counts[':'] += text.count(':')
            punctuation_counts[';'] += text.count(';')

        # Normalize by text length (per 1000 chars)
        rates = {}
        if total_chars > 0:
            for punct, count in punctuation_counts.items():
                rates[punct] = (count / total_chars) * 1000

        return rates

    def validate_voice(
        self,
        text: str,
        persona: str,
        return_details: bool = True
    ) -> Dict[str, Any]:
        """
        Validate if text matches the persona's voice.

        Args:
            text: Text to validate
            persona: Persona name (e.g., 'qronoya', 'aspandead')
            return_details: Whether to return detailed analysis

        Returns:
            Dict with validation results:
            - is_consistent: bool (overall pass/fail)
            - consistency_score: float (0-100)
            - issues: List[str] (detected problems)
            - warnings: List[str] (minor concerns)
            - details: Dict (detailed metrics if return_details=True)
        """
        if persona not in self.persona_profiles:
            logger.warning(f"No voice profile found for {persona}")
            return {
                'is_consistent': True,  # Pass by default if no profile
                'consistency_score': 50.0,
                'issues': [f"No voice profile available for {persona}"],
                'warnings': [],
                'details': {}
            }

        profile = self.persona_profiles[persona]

        # Calculate various consistency metrics
        vocab_score = self._check_vocabulary_overlap(text, profile)
        tone_score = self._check_tone_consistency(text, profile)
        pattern_score = self._check_pattern_consistency(text, profile)
        punct_score = self._check_punctuation_consistency(text, profile)

        # Detect off-brand language
        off_brand_words = self._detect_off_brand_language(text, profile)

        # Calculate overall consistency score (weighted average)
        consistency_score = (
            vocab_score * 0.30 +      # 30% weight on vocabulary
            tone_score * 0.25 +        # 25% weight on tone
            pattern_score * 0.25 +     # 25% weight on patterns
            punct_score * 0.20         # 20% weight on punctuation
        )

        # Determine if consistent (threshold: 60%)
        is_consistent = consistency_score >= 60.0

        # Collect issues and warnings
        issues = []
        warnings = []

        if vocab_score < 50:
            issues.append(f"Low vocabulary similarity ({vocab_score:.1f}%) - doesn't use typical words")

        if tone_score < 50:
            issues.append(f"Tone mismatch ({tone_score:.1f}%) - doesn't match expected voice")

        if pattern_score < 50:
            issues.append(f"Pattern mismatch ({pattern_score:.1f}%) - sentence structure doesn't match")

        if punct_score < 50:
            warnings.append(f"Unusual punctuation ({punct_score:.1f}%) - different from typical style")

        if off_brand_words:
            issues.append(f"Off-brand words detected: {', '.join(off_brand_words[:5])}")

        # Build result
        result = {
            'is_consistent': is_consistent,
            'consistency_score': round(consistency_score, 2),
            'issues': issues,
            'warnings': warnings
        }

        if return_details:
            result['details'] = {
                'vocabulary_score': round(vocab_score, 2),
                'tone_score': round(tone_score, 2),
                'pattern_score': round(pattern_score, 2),
                'punctuation_score': round(punct_score, 2),
                'off_brand_words': off_brand_words,
                'word_count': len(re.findall(r'\b\w+\b', text)),
                'sentence_count': len(re.split(r'[.!?]+', text))
            }

        logger.info(f"Voice validation for {persona}: {consistency_score:.1f}% ({'✅ PASS' if is_consistent else '❌ FAIL'})")

        return result

    def _check_vocabulary_overlap(self, text: str, profile: Dict[str, Any]) -> float:
        """Check what % of words in text are in persona's typical vocabulary"""
        text_words = set(re.findall(r'\b\w+\b', text.lower()))

        if not text_words:
            return 50.0  # Neutral score for empty text

        persona_vocab = profile.get('vocabulary', set())

        if not persona_vocab:
            return 50.0  # Neutral score if no profile data

        # Calculate overlap
        overlap = text_words.intersection(persona_vocab)
        overlap_rate = len(overlap) / len(text_words)

        # Convert to 0-100 scale
        # 0% overlap = 0 score, 50% overlap = 75 score, 100% overlap = 100 score
        score = min(100, overlap_rate * 150)

        return score

    def _check_tone_consistency(self, text: str, profile: Dict[str, Any]) -> float:
        """Check if tone matches persona's typical tone"""
        # Analyze text tone
        text_lower = text.lower()

        # Tone indicators
        casual_indicators = ['lol', 'btw', 'tbh', 'idk', 'ngl', 'fr', 'literally', 'honestly']
        formal_indicators = ['therefore', 'furthermore', 'moreover', 'consequently', 'thus', 'hence']
        emotional_indicators = ['!', '❤️', '😍', '🔥', '💯', 'amazing', 'incredible', 'love']
        analytical_indicators = ['data', 'analysis', 'research', 'study', 'evidence', 'shows', 'indicates']

        text_tone = {
            'casual': sum(1 for word in casual_indicators if word in text_lower),
            'formal': sum(1 for word in formal_indicators if word in text_lower),
            'emotional': sum(1 for ind in emotional_indicators if ind in text),
            'analytical': sum(1 for word in analytical_indicators if word in text_lower)
        }

        # Get expected tone from profile
        expected_tone = profile.get('tone', [])

        if not expected_tone:
            return 75.0  # Neutral-high score if no tone data

        # Score based on presence of expected tone indicators
        score = 75.0  # Start at neutral

        # Check if text matches expected tones
        if 'casual' in expected_tone and text_tone['casual'] > 0:
            score += 10
        elif 'casual' in expected_tone and text_tone['formal'] > 0:
            score -= 15

        if 'analytical' in expected_tone and text_tone['analytical'] > 0:
            score += 10
        elif 'analytical' in expected_tone and text_tone['casual'] > 2:
            score -= 15

        if 'emotional' in expected_tone and text_tone['emotional'] > 0:
            score += 10

        return max(0, min(100, score))

    def _check_pattern_consistency(self, text: str, profile: Dict[str, Any]) -> float:
        """Check if sentence patterns match persona's style"""
        patterns = profile.get('sentence_patterns', {})

        if not patterns:
            return 75.0  # Neutral-high score if no pattern data

        # Analyze text patterns
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 50.0

        text_patterns = {
            'avg_sentence_length': sum(len(s) for s in sentences) / len(sentences),
            'question_rate': sum(1 for s in sentences if '?' in s or s.lower().startswith(('what', 'why', 'how'))) / len(sentences)
        }

        # Compare patterns
        score = 75.0  # Start at neutral

        # Check sentence length similarity
        expected_length = patterns.get('avg_sentence_length', 100)
        length_diff = abs(text_patterns['avg_sentence_length'] - expected_length)

        if length_diff < 20:
            score += 15
        elif length_diff > 50:
            score -= 20

        # Check question rate
        expected_question_rate = patterns.get('question_rate', 0)
        question_diff = abs(text_patterns['question_rate'] - expected_question_rate)

        if question_diff < 0.1:
            score += 10
        elif question_diff > 0.3:
            score -= 10

        return max(0, min(100, score))

    def _check_punctuation_consistency(self, text: str, profile: Dict[str, Any]) -> float:
        """Check if punctuation usage matches persona's style"""
        punct_rates = profile.get('punctuation_style', {})

        if not punct_rates:
            return 75.0  # Neutral-high score if no punctuation data

        # Analyze text punctuation
        text_length = len(text)
        if text_length == 0:
            return 50.0

        text_punct = {
            '!': (text.count('!') / text_length) * 1000,
            '?': (text.count('?') / text_length) * 1000,
            '...': (text.count('...') / text_length) * 1000,
            '-': (text.count(' - ') / text_length) * 1000
        }

        # Compare with expected rates
        score = 75.0  # Start at neutral

        for punct, expected_rate in punct_rates.items():
            if punct in text_punct:
                text_rate = text_punct[punct]
                diff = abs(text_rate - expected_rate)

                # Small difference = good, large difference = bad
                if diff < expected_rate * 0.5:  # Within 50% of expected
                    score += 5
                elif diff > expected_rate * 2:  # More than 2x expected
                    score -= 10

        return max(0, min(100, score))

    def _detect_off_brand_language(self, text: str, profile: Dict[str, Any]) -> List[str]:
        """Detect words/phrases that are off-brand for this persona"""
        text_lower = text.lower()

        # Generic off-brand indicators (too corporate/formal)
        corporate_phrases = [
            'leverage', 'synergy', 'paradigm', 'holistic', 'disruptive',
            'cutting-edge', 'state-of-the-art', 'innovative solution',
            'best practices', 'core competency', 'going forward'
        ]

        # AI-generated tells (too obvious)
        ai_tells = [
            'delve into', 'it\'s important to note', 'in conclusion',
            'furthermore', 'moreover', 'nevertheless', 'consequently'
        ]

        off_brand = []

        # Check for corporate language
        for phrase in corporate_phrases:
            if phrase in text_lower:
                off_brand.append(phrase)

        # Check for AI tells
        for phrase in ai_tells:
            if phrase in text_lower:
                off_brand.append(phrase)

        return off_brand[:10]  # Return max 10

    def batch_validate(
        self,
        texts: List[str],
        persona: str
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple texts at once.

        Args:
            texts: List of texts to validate
            persona: Persona name

        Returns:
            List of validation results (one per text)
        """
        results = []

        for i, text in enumerate(texts):
            logger.info(f"Validating text {i+1}/{len(texts)} for {persona}")
            result = self.validate_voice(text, persona, return_details=True)
            results.append(result)

        return results

    def get_improvement_suggestions(
        self,
        validation_result: Dict[str, Any],
        persona: str
    ) -> List[str]:
        """
        Generate specific suggestions to improve voice consistency.

        Args:
            validation_result: Result from validate_voice()
            persona: Persona name

        Returns:
            List of actionable suggestions
        """
        suggestions = []

        if persona not in self.persona_profiles:
            return ["No voice profile available for suggestions"]

        profile = self.persona_profiles[persona]
        details = validation_result.get('details', {})

        # Vocabulary suggestions
        vocab_score = details.get('vocabulary_score', 100)
        if vocab_score < 60:
            common_words = profile.get('common_words', [])[:10]
            if common_words:
                words_list = ', '.join([w for w, _ in common_words])
                suggestions.append(f"Use more typical {persona} vocabulary like: {words_list}")

        # Tone suggestions
        tone_score = details.get('tone_score', 100)
        if tone_score < 60:
            expected_tone = profile.get('tone', [])
            if expected_tone:
                suggestions.append(f"Adjust tone to be more: {', '.join(expected_tone)}")

        # Pattern suggestions
        pattern_score = details.get('pattern_score', 100)
        if pattern_score < 60:
            patterns = profile.get('sentence_patterns', {})
            avg_length = patterns.get('avg_sentence_length')
            if avg_length:
                suggestions.append(f"Adjust sentence length (typical: ~{int(avg_length)} chars)")

        # Off-brand word suggestions
        off_brand = details.get('off_brand_words', [])
        if off_brand:
            suggestions.append(f"Remove off-brand language: {', '.join(off_brand[:3])}")

        # General suggestion if still low score
        if validation_result.get('consistency_score', 100) < 60:
            suggestions.append("Study more examples from this persona to better match their voice")

        return suggestions
