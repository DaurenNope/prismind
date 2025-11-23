"""
Advanced Quality Scorer with Engagement Prediction
Implements sophisticated scoring algorithms for content quality and performance prediction
"""

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class QualityDimension:
    """Individual quality dimension score"""
    name: str
    score: float
    weight: float
    explanation: str
    suggestions: List[str]

@dataclass
class EngagementPrediction:
    """Detailed engagement prediction"""
    predicted_engagement_rate: float
    confidence_interval: Tuple[float, float]
    key_drivers: List[str]
    risk_factors: List[str]
    optimization_potential: float

class AdvancedQualityScorer:
    """Advanced quality scoring with ML-inspired techniques"""

    def __init__(self):
        self.quality_weights = self._load_quality_weights()
        self.engagement_patterns = self._load_engagement_patterns()
        self.platform_benchmarks = self._load_platform_benchmarks()

    def _load_quality_weights(self) -> Dict[str, Dict[str, float]]:
        """Load quality weights for different platforms and content types"""
        return {
            'twitter': {
                'engagement_hooks': 0.25,
                'voice_consistency': 0.20,
                'clarity_conciseness': 0.20,
                'emotional_impact': 0.15,
                'platform_fit': 0.10,
                'readability': 0.10
            },
            'linkedin': {
                'professionalism': 0.25,
                'value_proposition': 0.20,
                'authority_indicators': 0.20,
                'structure_quality': 0.15,
                'engagement_potential': 0.10,
                'industry_relevance': 0.10
            },
            'threads': {
                'authenticity': 0.25,
                'conversational_tone': 0.20,
                'relatability': 0.20,
                'engagement_hooks': 0.15,
                'visual_appeal': 0.10,
                'trending_alignment': 0.10
            },
            'telegram': {
                'information_value': 0.25,
                'clarity': 0.20,
                'actionability': 0.20,
                'community_value': 0.15,
                'relevance': 0.10,
                'shareability': 0.10
            }
        }

    def _load_engagement_patterns(self) -> Dict[str, float]:
        """Load known engagement patterns"""
        return {
            'question_power': 0.8,           # Questions get 2x engagement
            'emoji_boost': 0.3,              # Emojis increase engagement
            'storytelling_power': 1.2,       # Stories get high engagement
            'authority_boost': 0.5,          # Authority indicators help
            'urgency_effect': 0.4,           # Urgency drives action
            'call_to_action_power': 0.6,     # CTAs increase conversions
            'emotional_connection': 0.9,     # Emotions drive sharing
            'value_proposition': 0.7,        # Clear value helps
            'social_proof': 0.5,             # Social proof builds trust
            'controversy_spark': 1.5         # Controversy increases engagement
        }

    def _load_platform_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Load platform-specific benchmarks"""
        return {
            'twitter': {
                'optimal_length': {'min': 50, 'max': 240},
                'optimal_sentences': {'min': 1, 'max': 4},
                'emoji_density': {'min': 0.02, 'max': 0.1},
                'hashtag_count': {'min': 0, 'max': 2}
            },
            'linkedin': {
                'optimal_length': {'min': 100, 'max': 600},
                'optimal_sentences': {'min': 3, 'max': 8},
                'professional_terms': {'min': 2, 'max': 10},
                'structure_score': {'min': 0.6, 'max': 1.0}
            },
            'threads': {
                'optimal_length': {'min': 80, 'max': 300},
                'optimal_sentences': {'min': 2, 'max': 6},
                'casual_indicators': {'min': 1, 'max': 5},
                'personal_references': {'min': 0, 'max': 3}
            }
        }

    def calculate_comprehensive_quality_score(self, content: str, persona_data: Dict,
                                            platform: str, voice_analysis: Optional[Dict] = None) -> Dict[str, Any]:
        """Calculate comprehensive quality score with detailed breakdown"""

        try:
            # Get platform-specific weights
            weights = self.quality_weights.get(platform, self.quality_weights['twitter'])

            # Calculate individual quality dimensions
            dimensions = []

            # Voice consistency
            voice_score = self._calculate_voice_consistency(content, persona_data, voice_analysis)
            dimensions.append(QualityDimension(
                name="voice_consistency",
                score=voice_score,
                weight=weights.get('voice_consistency', 0.2),
                explanation="How well the content matches the persona's voice patterns",
                suggestions=self._get_voice_consistency_suggestions(voice_score)
            ))

            # Platform fit
            platform_score = self._calculate_platform_fit(content, platform)
            dimensions.append(QualityDimension(
                name="platform_fit",
                score=platform_score,
                weight=weights.get('platform_fit', 0.1),
                explanation=f"How well the content fits {platform} best practices",
                suggestions=self._get_platform_fit_suggestions(platform_score, platform)
            ))

            # Engagement hooks
            engagement_score = self._calculate_engagement_hooks(content, platform)
            dimensions.append(QualityDimension(
                name="engagement_hooks",
                score=engagement_score,
                weight=weights.get('engagement_hooks', 0.2),
                explanation="Presence and quality of engagement-driving elements",
                suggestions=self._get_engagement_suggestions(engagement_score)
            ))

            # Clarity and conciseness
            clarity_score = self._calculate_clarity_conciseness(content, platform)
            dimensions.append(QualityDimension(
                name="clarity_conciseness",
                score=clarity_score,
                weight=weights.get('clarity_conciseness', 0.2),
                explanation="How clear, readable, and well-structured the content is",
                suggestions=self._get_clarity_suggestions(clarity_score)
            ))

            # Emotional impact
            emotional_score = self._calculate_emotional_impact(content)
            dimensions.append(QualityDimension(
                name="emotional_impact",
                score=emotional_score,
                weight=weights.get('emotional_impact', 0.15),
                explanation="Emotional resonance and connection potential",
                suggestions=self._get_emotional_suggestions(emotional_score)
            ))

            # Platform-specific dimensions
            if platform == 'linkedin':
                professionalism_score = self._calculate_professionalism(content)
                dimensions.append(QualityDimension(
                    name="professionalism",
                    score=professionalism_score,
                    weight=weights.get('professionalism', 0.25),
                    explanation="Professional language and business value",
                    suggestions=self._get_professionalism_suggestions(professionalism_score)
                ))

                value_score = self._calculate_value_proposition(content)
                dimensions.append(QualityDimension(
                    name="value_proposition",
                    score=value_score,
                    weight=weights.get('value_proposition', 0.2),
                    explanation="Clear value proposition for readers",
                    suggestions=self._get_value_suggestions(value_score)
                ))

            elif platform == 'threads':
                authenticity_score = self._calculate_authenticity(content)
                dimensions.append(QualityDimension(
                    name="authenticity",
                    score=authenticity_score,
                    weight=weights.get('authenticity', 0.25),
                    explanation="Authenticity and genuine tone",
                    suggestions=self._get_authenticity_suggestions(authenticity_score)
                ))

                conversational_score = self._calculate_conversational_tone(content)
                dimensions.append(QualityDimension(
                    name="conversational_tone",
                    score=conversational_score,
                    weight=weights.get('conversational_tone', 0.2),
                    explanation="Conversational and approachable tone",
                    suggestions=self._get_conversational_suggestions(conversational_score)
                ))

            # Calculate weighted overall score
            overall_score = sum(d.score * d.weight for d in dimensions)

            # Calculate engagement prediction
            engagement_pred = self._predict_engagement(content, platform, dimensions)

            # Identify optimization opportunities
            optimization_opp = self._identify_optimization_opportunities(dimensions)

            return {
                'overall_score': overall_score,
                'dimensions': [
                    {
                        'name': d.name,
                        'score': d.score,
                        'weight': d.weight,
                        'weighted_score': d.score * d.weight,
                        'explanation': d.explanation,
                        'suggestions': d.suggestions
                    }
                    for d in dimensions
                ],
                'engagement_prediction': engagement_pred,
                'optimization_opportunities': optimization_opp,
                'confidence_score': self._calculate_confidence_score(dimensions),
                'grade': self._calculate_quality_grade(overall_score),
                'key_strengths': [d.name for d in dimensions if d.score >= 0.7],
                'improvement_areas': [d.name for d in dimensions if d.score < 0.5]
            }

        except Exception as e:
            logger.error(f"Quality scoring failed: {e}")
            return self._fallback_quality_score()

    def _calculate_voice_consistency(self, content: str, persona_data: Dict,
                                   voice_analysis: Optional[Dict] = None) -> float:
        """Calculate voice consistency with persona"""

        if not voice_analysis:
            return 0.5  # Default when no voice analysis available

        # Extract persona examples
        examples = persona_data.get('examples', [])
        if not examples:
            return 0.5

        # Calculate linguistic similarity
        content_words = set(content.lower().split())
        example_words = set()
        for example in examples:
            example_words.update(example.lower().split())

        # Jaccard similarity
        intersection = len(content_words.intersection(example_words))
        union = len(content_words.union(example_words))
        similarity = intersection / max(union, 1)

        # Adjust for sentence structure
        content_sent_count = len(re.split(r'[.!?]+', content))
        avg_sent_length = len(content.split()) / max(content_sent_count, 1)

        example_sent_lengths = []
        for example in examples:
            sents = re.split(r'[.!?]+', example)
            example_sent_lengths.extend([len(s.split()) for s in sents if s.strip()])

        if example_sent_lengths:
            avg_example_sent_length = np.mean(example_sent_lengths)
            sent_similarity = 1.0 - min(1.0, abs(avg_sent_length - avg_example_sent_length) / 10.0)
        else:
            sent_similarity = 0.5

        # Combine metrics
        return (similarity * 0.6 + sent_similarity * 0.4)

    def _calculate_platform_fit(self, content: str, platform: str) -> float:
        """Calculate how well content fits platform best practices"""
        benchmarks = self.platform_benchmarks.get(platform, {})
        score = 0.5  # Base score
        factors = []

        # Length optimization
        length_benchmarks = benchmarks.get('optimal_length', {})
        content_length = len(content)
        if length_benchmarks:
            if length_benchmarks.get('min', 0) <= content_length <= length_benchmarks.get('max', 999999):
                score += 0.2

        # Sentence count optimization
        sent_benchmarks = benchmarks.get('optimal_sentences', {})
        content_sentences = len(re.split(r'[.!?]+', content))
        if sent_benchmarks:
            if sent_benchmarks.get('min', 0) <= content_sentences <= sent_benchmarks.get('max', 999):
                score += 0.15

        # Platform-specific checks
        if platform == 'twitter':
            # Check for hashtags
            hashtag_count = content.count('#')
            if 0 <= hashtag_count <= 2:
                score += 0.1
            # Check emoji density
            emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', content))
            emoji_density = emoji_count / max(len(content.split()), 1)
            if 0.02 <= emoji_density <= 0.1:
                score += 0.1

        elif platform == 'linkedin':
            # Professional language check
            professional_words = ['innovation', 'strategy', 'leadership', 'growth', 'opportunity',
                                'expertise', 'collaboration', 'synergy', 'optimization']
            words = content.lower().split()
            professional_count = sum(1 for word in words if word in professional_words)
            if professional_count >= 2:
                score += 0.15

        elif platform == 'threads':
            # Casual tone indicators
            casual_indicators = ['lol', 'omg', 'literally', 'basically', 'super', 'totally', 'like']
            words = content.lower().split()
            casual_count = sum(1 for word in words if word in casual_indicators)
            if 1 <= casual_count <= 3:
                score += 0.15

        return min(1.0, score)

    def _calculate_engagement_hooks(self, content: str, platform: str) -> float:
        """Calculate presence and quality of engagement hooks"""
        score = 0.0
        hooks_found = []

        # Questions
        if '?' in content:
            score += 0.3
            hooks_found.append('questions')

        # Emojis
        if re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', content):
            score += 0.2
            hooks_found.append('emojis')

        # Call to action
        cta_phrases = ['click here', 'link in bio', 'check out', 'visit', 'join', 'subscribe', 'follow']
        content_lower = content.lower()
        if any(phrase in content_lower for phrase in cta_phrases):
            score += 0.25
            hooks_found.append('call_to_action')

        # Storytelling elements
        story_indicators = ['i remember', 'when i', 'the story', 'experience', 'journey', 'path']
        if any(indicator in content_lower for indicator in story_indicators):
            score += 0.25
            hooks_found.append('storytelling')

        return min(1.0, score)

    def _calculate_clarity_conciseness(self, content: str, platform: str) -> float:
        """Calculate clarity and conciseness score"""
        score = 0.5  # Base score

        # Sentence length analysis
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
        if sentences:
            avg_sentence_length = np.mean([len(s.split()) for s in sentences])

            # Optimal sentence length is 10-20 words
            if 10 <= avg_sentence_length <= 20:
                score += 0.2
            elif avg_sentence_length <= 30:
                score += 0.1

        # Word complexity
        words = content.split()
        if words:
            avg_word_length = np.mean([len(word) for word in words])
            # Optimal average word length is 4-6 characters
            if 4 <= avg_word_length <= 6:
                score += 0.15

        # Passive voice detection (simplified)
        passive_indicators = ['is', 'are', 'was', 'were', 'been', 'being'] + ['by', 'was', 'were']
        passive_count = sum(1 for word in words if word.lower() in passive_indicators)
        passive_ratio = passive_count / max(len(words), 1)
        if passive_ratio < 0.15:  # Less than 15% passive voice
            score += 0.15

        return min(1.0, score)

    def _calculate_emotional_impact(self, content: str) -> float:
        """Calculate emotional impact and resonance"""
        positive_emotions = ['amazing', 'incredible', 'fantastic', 'awesome', 'great', 'love', 'excited',
                           'happy', 'wonderful', 'brilliant', 'outstanding', 'spectacular']
        negative_emotions = ['terrible', 'awful', 'horrible', 'hate', 'disappointed', 'frustrated',
                           'angry', 'sad', 'depressed', 'worried', 'concerned']

        words = content.lower().split()

        # Emotional word density
        positive_count = sum(1 for word in words if word in positive_emotions)
        negative_count = sum(1 for word in words if word in negative_emotions)
        emotional_density = (positive_count + negative_count) / max(len(words), 1)

        # Exclamation marks indicate emotion
        exclamation_count = content.count('!')
        exclamation_density = exclamation_count / max(len(content), 1)

        # Emotional impact score
        emotional_score = min(1.0, emotional_density * 10 + exclamation_density * 5)

        return emotional_score

    def _calculate_professionalism(self, content: str) -> float:
        """Calculate professionalism score for LinkedIn"""
        professional_terms = ['innovation', 'strategy', 'leadership', 'growth', 'opportunity',
                            'expertise', 'collaboration', 'synergy', 'optimization', 'efficiency',
                            'development', 'management', 'analysis', 'research', 'performance']

        words = content.lower().split()
        professional_count = sum(1 for word in words if word in professional_terms)
        professional_density = professional_count / max(len(words), 1)

        # Avoid overly casual language
        casual_terms = ['lol', 'omg', 'like', 'totally', 'super', 'awesome', 'cool']
        casual_count = sum(1 for word in words if word in casual_terms)
        casual_penalty = min(0.3, casual_count * 0.1)

        professionalism = max(0.0, professional_density * 2 - casual_penalty)
        return min(1.0, professionalism)

    def _calculate_authenticity(self, content: str) -> float:
        """Calculate authenticity score for Threads"""
        # Personal pronouns indicate authenticity
        personal_pronouns = ['i', 'my', 'me', 'we', 'our', 'us']
        words = content.lower().split()
        personal_count = sum(1 for word in words if word in personal_pronouns)
        personal_density = personal_count / max(len(words), 1)

        # Avoid overly perfect or corporate language
        corporate_terms = ['synergy', 'leverage', 'paradigm', 'optimize', 'streamline']
        corporate_count = sum(1 for word in words if word in corporate_terms)
        corporate_penalty = min(0.4, corporate_count * 0.1)

        authenticity = max(0.0, personal_density * 3 - corporate_penalty)
        return min(1.0, authenticity)

    def _predict_engagement(self, content: str, platform: str, dimensions: List[QualityDimension]) -> EngagementPrediction:
        """Predict engagement based on quality dimensions"""

        # Base engagement rate by platform
        base_rates = {
            'twitter': 0.05,    # 5% engagement rate
            'linkedin': 0.08,   # 8% engagement rate
            'threads': 0.12,    # 12% engagement rate
            'telegram': 0.15    # 15% engagement rate
        }

        base_rate = base_rates.get(platform, 0.07)

        # Quality multiplier
        quality_multiplier = sum(d.score * d.weight for d in dimensions)

        # Engagement hooks multiplier
        engagement_hooks = next((d for d in dimensions if d.name == 'engagement_hooks'), None)
        hooks_multiplier = 1.0 + (engagement_hooks.score * 0.5 if engagement_hooks else 0)

        # Predict engagement rate
        predicted_rate = base_rate * quality_multiplier * hooks_multiplier

        # Confidence interval (simplified)
        margin_of_error = 0.02 * (2.0 - quality_multiplier)  # Lower quality = higher uncertainty
        confidence_interval = (
            max(0, predicted_rate - margin_of_error),
            min(1, predicted_rate + margin_of_error)
        )

        # Key drivers
        key_drivers = [d.name for d in dimensions if d.score >= 0.7]
        risk_factors = [d.name for d in dimensions if d.score <= 0.4]

        # Optimization potential
        optimization_potential = sum(max(0, 0.7 - d.score) * d.weight for d in dimensions) * 100

        return EngagementPrediction(
            predicted_engagement_rate=predicted_rate,
            confidence_interval=confidence_interval,
            key_drivers=key_drivers,
            risk_factors=risk_factors,
            optimization_potential=optimization_potential
        )

    def _identify_optimization_opportunities(self, dimensions: List[QualityDimension]) -> List[Dict[str, Any]]:
        """Identify specific optimization opportunities"""
        opportunities = []

        for dimension in dimensions:
            if dimension.score < 0.6:  # Below 60% needs optimization
                impact = dimension.weight * (1.0 - dimension.score)
                opportunities.append({
                    'dimension': dimension.name,
                    'current_score': dimension.score,
                    'potential_improvement': 1.0 - dimension.score,
                    'impact': impact,
                    'priority': 'high' if impact > 0.15 else 'medium' if impact > 0.08 else 'low',
                    'suggestions': dimension.suggestions[:3]  # Top 3 suggestions
                })

        # Sort by impact
        opportunities.sort(key=lambda x: x['impact'], reverse=True)

        return opportunities

    def _calculate_confidence_score(self, dimensions: List[QualityDimension]) -> float:
        """Calculate confidence in the quality assessment"""
        # Higher confidence when dimensions are consistent
        scores = [d.score for d in dimensions]
        mean_score = np.mean(scores)
        score_std = np.std(scores) if len(scores) > 1 else 0

        # Confidence based on consistency and average score
        consistency_factor = max(0.5, 1.0 - score_std)
        quality_factor = mean_score

        return min(0.95, (consistency_factor * 0.6 + quality_factor * 0.4))

    def _calculate_quality_grade(self, overall_score: float) -> str:
        """Calculate letter grade for quality score"""
        if overall_score >= 0.9:
            return 'A+'
        elif overall_score >= 0.85:
            return 'A'
        elif overall_score >= 0.8:
            return 'A-'
        elif overall_score >= 0.75:
            return 'B+'
        elif overall_score >= 0.7:
            return 'B'
        elif overall_score >= 0.65:
            return 'B-'
        elif overall_score >= 0.6:
            return 'C+'
        elif overall_score >= 0.5:
            return 'C'
        else:
            return 'D'

    def _get_voice_consistency_suggestions(self, score: float) -> List[str]:
        """Get suggestions for improving voice consistency"""
        if score < 0.5:
            return [
                "Review persona examples more carefully",
                "Use similar sentence structures to examples",
                "Incorporate key phrases from persona examples",
                "Match the tone and style more closely"
            ]
        elif score < 0.7:
            return [
                "Add more persona-specific language",
                "Adjust sentence length to match examples",
                "Incorporate more characteristic phrases"
            ]
        else:
            return ["Voice consistency is good"]

    def _get_platform_fit_suggestions(self, score: float, platform: str) -> List[str]:
        """Get platform-specific fit suggestions"""
        if platform == 'twitter':
            if score < 0.6:
                return [
                    "Keep content under 280 characters",
                    "Add relevant hashtags (1-2 max)",
                    "Include emojis for visual appeal"
                ]
        elif platform == 'linkedin':
            if score < 0.6:
                return [
                    "Use more professional language",
                    "Include business insights or data",
                    "Structure content with clear paragraphs"
                ]
        elif platform == 'threads':
            if score < 0.6:
                return [
                    "Use more conversational tone",
                    "Add personal touches and experiences",
                    "Keep it casual and approachable"
                ]
        return ["Content fits platform well"]

    def _get_engagement_suggestions(self, score: float) -> List[str]:
        """Get engagement improvement suggestions"""
        if score < 0.5:
            return [
                "Add a question to encourage responses",
                "Include relevant emojis",
                "Add a clear call-to-action",
                "Include a personal story or experience"
            ]
        elif score < 0.7:
            return [
                "Add one engagement element",
                "Consider adding a question or emoji"
            ]
        return ["Engagement hooks are well implemented"]

    def _get_clarity_suggestions(self, score: float) -> List[str]:
        """Get clarity improvement suggestions"""
        if score < 0.5:
            return [
                "Use shorter sentences (10-20 words)",
                "Avoid complex vocabulary",
                "Break up long paragraphs",
                "Use active voice instead of passive"
            ]
        elif score < 0.7:
            return [
                "Simplify complex sentences",
                "Check for passive voice usage"
            ]
        return ["Content is clear and well-structured"]

    def _get_emotional_suggestions(self, score: float) -> List[str]:
        """Get emotional impact suggestions"""
        if score < 0.5:
            return [
                "Add emotional words (amazing, incredible, etc.)",
                "Include exclamation points for emphasis",
                "Share personal feelings or excitement"
            ]
        elif score < 0.7:
            return [
                "Add one emotional element",
                "Consider showing more enthusiasm"
            ]
        return ["Emotional impact is well balanced"]

    def _get_professionalism_suggestions(self, score: float) -> List[str]:
        """Get professionalism suggestions"""
        if score < 0.5:
            return [
                "Use more industry terminology",
                "Include business insights or data",
                "Avoid overly casual language",
                "Add professional context or experience"
            ]
        elif score < 0.7:
            return [
                "Include more business value",
                "Add professional terminology"
            ]
        return ["Professional tone is appropriate"]

    def _calculate_value_proposition(self, content: str) -> float:
        """Calculate value proposition score for LinkedIn"""
        value_indicators = ['benefit', 'advantage', 'improve', 'increase', 'reduce', 'save', 'gain', 'achieve']
        words = content.lower().split()
        value_count = sum(1 for word in words if word in value_indicators)

        # Check for specific outcomes
        outcome_indicators = ['results', 'outcomes', 'impact', 'success', 'performance', 'growth']
        outcome_count = sum(1 for indicator in outcome_indicators if indicator in content.lower())

        value_density = (value_count + outcome_count) / max(len(words), 1)
        return min(1.0, value_density * 5)

    def _calculate_conversational_tone(self, content: str) -> float:
        """Calculate conversational tone score for Threads"""
        conversational_indicators = ['you know', 'i mean', 'like', 'basically', 'literally', 'honestly', 'actually']
        content_lower = content.lower()
        conv_count = sum(1 for indicator in conversational_indicators if indicator in content_lower)

        # Check for questions and direct address
        has_question = '?' in content
        direct_address = content_lower.count(' you ') + content_lower.count('your')

        conversational_score = min(1.0, conv_count * 0.3 + (has_question * 0.2) + (direct_address * 0.1))
        return conversational_score

    def _get_value_suggestions(self, score: float) -> List[str]:
        """Get value proposition suggestions"""
        if score < 0.5:
            return [
                "Clearly state the value proposition",
                "Explain benefits to the reader",
                "Include actionable insights",
                "Add specific takeaways"
            ]
        elif score < 0.7:
            return [
                "Strengthen the value proposition",
                "Make benefits more explicit"
            ]
        return ["Value proposition is clear"]

    def _get_authenticity_suggestions(self, score: float) -> List[str]:
        """Get authenticity suggestions"""
        if score < 0.5:
            return [
                "Use more personal pronouns (I, my, we)",
                "Share personal experiences",
                "Avoid corporate jargon",
                "Show genuine emotion or excitement"
            ]
        elif score < 0.7:
            return [
                "Add more personal touches",
                "Show more genuine feeling"
            ]
        return ["Authenticity comes through well"]

    def _get_conversational_suggestions(self, score: float) -> List[str]:
        """Get conversational tone suggestions"""
        if score < 0.5:
            return [
                "Use more conversational language",
                "Add rhetorical questions",
                "Write as if talking to a friend",
                "Use contractions (it's, you're, etc.)"
            ]
        elif score < 0.7:
            return [
                "Make language more conversational",
                "Add some casual elements"
            ]
        return ["Conversational tone is natural"]

    def _fallback_quality_score(self) -> Dict[str, Any]:
        """Fallback quality score when analysis fails"""
        return {
            'overall_score': 0.5,
            'dimensions': [],
            'engagement_prediction': EngagementPrediction(
                predicted_engagement_rate=0.05,
                confidence_interval=(0.02, 0.08),
                key_drivers=[],
                risk_factors=['Analysis failed'],
                optimization_potential=50.0
            ),
            'optimization_opportunities': [],
            'confidence_score': 0.3,
            'grade': 'C',
            'key_strengths': [],
            'improvement_areas': ['General quality improvement needed']
        }