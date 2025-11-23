"""
Machine Learning Insights for Content Optimization
Provides advanced analytics and predictions for persona performance
"""

import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class EngagementPrediction:
    """Predicted engagement metrics for content"""
    predicted_likes: float
    predicted_shares: float
    predicted_comments: float
    confidence_score: float
    viral_potential: float
    optimal_posting_time: str

@dataclass
class ContentInsight:
    """ML-powered insight about content performance"""
    insight_type: str
    description: str
    confidence: float
    actionable_recommendation: str
    expected_improvement: float

class ContentAnalyzer:
    """Advanced content analysis using ML-inspired techniques"""

    def __init__(self):
        self.engagement_patterns = {}
        self.viral_indicators = self._load_viral_indicators()
        self.persona_performance_history = defaultdict(list)

    def _load_viral_indicators(self) -> Dict[str, float]:
        """Load known indicators of viral content"""
        return {
            'question_hooks': 0.8,          # Questions drive engagement
            'emotional_words': 0.7,          # Emotions trigger shares
            'surprise_elements': 0.9,        # Surprise drives virality
            'call_to_action': 0.6,           # CTAs increase engagement
            'relatable_stories': 0.8,        # Stories get shared
            'trending_topics': 0.7,          # Trending content performs
            'controversial_opinions': 0.5,   # High engagement but risky
            'educational_value': 0.6,        # Useful content gets saved
            'entertainment_value': 0.8,      # Entertainment gets shared
            'authenticity_score': 0.9        # Authenticity builds trust
        }

    def analyze_content_performance(self, content: str, persona_data: Dict,
                                   platform: str, historical_data: Optional[List] = None) -> Dict[str, Any]:
        """Comprehensive ML-inspired content analysis"""

        try:
            # Extract features
            features = self._extract_content_features(content, platform)

            # Predict engagement
            engagement = self._predict_engagement(features, persona_data, platform)

            # Generate insights
            insights = self._generate_insights(features, persona_data, platform, engagement)

            # Calculate viral potential
            viral_score = self._calculate_viral_potential(features, engagement)

            # Recommend optimizations
            optimizations = self._recommend_optimizations(features, insights, platform)

            # Store for learning
            self._store_performance_data(persona_data.get('id'), platform, features, engagement)

            return {
                'engagement_prediction': engagement,
                'viral_potential': viral_score,
                'content_insights': insights,
                'optimization_recommendations': optimizations,
                'feature_analysis': features,
                'confidence_score': self._calculate_confidence(features, historical_data)
            }

        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return self._fallback_analysis(content, platform)

    def _extract_content_features(self, content: str, platform: str) -> Dict[str, float]:
        """Extract ML-friendly features from content"""

        features = {}

        # Basic text features
        features['length'] = len(content)
        features['word_count'] = len(content.split())
        features['sentence_count'] = len(re.split(r'[.!?]+', content))
        features['avg_word_length'] = np.mean([len(word) for word in content.split()]) if content.split() else 0

        # Engagement features
        features['has_question'] = float('?' in content)
        features['has_emoji'] = float(bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', content)))
        features['hashtag_count'] = content.count('#')
        features['mention_count'] = content.count('@')
        features['exclamation_count'] = content.count('!')

        # Emotional features
        positive_words = ['amazing', 'incredible', 'fantastic', 'awesome', 'great', 'love', 'excited', 'happy']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'disappointed', 'frustrated', 'angry']

        words_lower = content.lower().split()
        features['positive_sentiment'] = sum(1 for word in words_lower if word in positive_words) / max(len(words_lower), 1)
        features['negative_sentiment'] = sum(1 for word in words_lower if word in negative_words) / max(len(words_lower), 1)

        # Urgency and scarcity
        urgency_words = ['now', 'today', 'limited', 'urgent', 'dont miss', 'only', 'hurry', 'fast']
        features['urgency_score'] = sum(1 for word in words_lower if word in urgency_words) / max(len(words_lower), 1)

        # Authority and credibility
        authority_words = ['research', 'study', 'expert', 'proven', 'data', 'analysis', 'results', 'evidence']
        features['authority_score'] = sum(1 for word in words_lower if word in authority_words) / max(len(words_lower), 1)

        # Platform-specific features
        if platform == 'twitter':
            features['within_limit'] = float(len(content) <= 280)
        elif platform == 'linkedin':
            features['professional_language'] = self._assess_professional_language(content)
        elif platform == 'threads':
            features['casual_tone'] = self._assess_casual_tone(content)

        # Storytelling elements
        story_indicators = ['i remember', 'when i', 'the story', 'experience', 'journey', 'path']
        features['storytelling_score'] = sum(1 for word in story_indicators if word in content.lower()) / len(story_indicators)

        # Call to action
        cta_phrases = ['click here', 'link in bio', 'check out', 'visit', 'join', 'subscribe', 'follow']
        features['cta_strength'] = sum(1 for phrase in cta_phrases if phrase in content.lower()) / len(cta_phrases)

        return features

    def _assess_professional_language(self, content: str) -> float:
        """Assess professional language level for LinkedIn"""
        professional_words = ['innovation', 'strategy', 'leadership', 'growth', 'opportunity', 'development',
                            'expertise', 'collaboration', 'synergy', 'optimization', 'efficiency']
        words_lower = content.lower().split()
        return sum(1 for word in words_lower if word in professional_words) / max(len(words_lower), 1)

    def _assess_casual_tone(self, content: str) -> float:
        """Assess casual tone for Threads"""
        casual_indicators = ['lol', 'omg', 'literally', 'basically', 'super', 'totally', 'like', 'pretty sure']
        words_lower = content.lower().split()
        return sum(1 for word in words_lower if word in casual_indicators) / max(len(words_lower), 1)

    def _predict_engagement(self, features: Dict[str, float], persona_data: Dict, platform: str) -> EngagementPrediction:
        """Predict engagement metrics using feature weights"""

        # Platform-specific base engagement rates
        base_rates = {
            'twitter': {'likes': 2.5, 'shares': 0.8, 'comments': 0.3},
            'linkedin': {'likes': 3.2, 'shares': 1.2, 'comments': 0.8},
            'threads': {'likes': 4.1, 'shares': 1.5, 'comments': 1.1},
            'telegram': {'views': 50, 'reactions': 2.0, 'comments': 0.5}
        }

        base = base_rates.get(platform, {'likes': 2.0, 'shares': 1.0, 'comments': 0.5})

        # Feature weights (simplified ML model)
        weights = {
            'has_question': 1.3,
            'has_emoji': 1.2,
            'positive_sentiment': 1.5,
            'urgency_score': 1.4,
            'authority_score': 1.2,
            'storytelling_score': 1.6,
            'cta_strength': 1.3,
            'within_limit': 1.1,
            'professional_language': 1.2,
            'casual_tone': 1.1
        }

        # Calculate engagement multipliers
        multiplier = 1.0
        for feature, weight in weights.items():
            if feature in features:
                multiplier *= (1.0 + (features[feature] * (weight - 1.0)))

        # Persona adjustment
        persona_multiplier = self._get_persona_multiplier(persona_data, platform)

        # Predict final engagement
        predicted_likes = base['likes'] * multiplier * persona_multiplier
        predicted_shares = base['shares'] * multiplier * persona_multiplier
        predicted_comments = base['comments'] * multiplier * persona_multiplier

        # Calculate viral potential
        viral_factors = [
            features.get('storytelling_score', 0) * 2.0,
            features.get('has_question', 0) * 1.5,
            features.get('positive_sentiment', 0) * 1.8,
            features.get('urgency_score', 0) * 1.3
        ]
        viral_potential = min(0.95, np.mean(viral_factors))

        # Confidence based on feature completeness
        confidence = min(0.95, len([f for f in features.values() if f > 0]) / len(features))

        return EngagementPrediction(
            predicted_likes=predicted_likes,
            predicted_shares=predicted_shares,
            predicted_comments=predicted_comments,
            confidence_score=confidence,
            viral_potential=viral_potential,
            optimal_posting_time=self._predict_optimal_time(persona_data, platform)
        )

    def _get_persona_multiplier(self, persona_data: Dict, platform: str) -> float:
        """Get persona-specific engagement multiplier"""
        persona_id = persona_data.get('id', '')

        # Look up historical performance
        if persona_id in self.persona_performance_history:
            history = self.persona_performance_history[persona_id][-10:]  # Last 10 performances
            if history:
                avg_performance = np.mean([h['engagement_score'] for h in history])
                return min(2.0, max(0.5, avg_performance))

        # Default multipliers based on persona type
        persona_name = persona_data.get('name', '').lower()
        if 'tech' in persona_name or 'founder' in persona_name:
            return 1.2 if platform == 'twitter' else 1.0
        elif 'academic' in persona_name or 'researcher' in persona_name:
            return 1.3 if platform == 'linkedin' else 0.9
        elif 'marketing' in persona_name or 'influencer' in persona_name:
            return 1.4 if platform in ['threads', 'twitter'] else 1.1
        else:
            return 1.0

    def _predict_optimal_time(self, persona_data: Dict, platform: str) -> str:
        """Predict optimal posting time based on persona and platform"""
        # Simplified time prediction based on persona type
        persona_name = persona_data.get('name', '').lower()

        if 'tech' in persona_name or 'founder' in persona_name:
            return "9:00 AM - 11:00 AM PST"  # Tech professionals active hours
        elif 'academic' in persona_name or 'researcher' in persona_name:
            return "2:00 PM - 4:00 PM PST"   # Academic reading hours
        elif 'marketing' in persona_name or 'influencer' in persona_name:
            return "6:00 PM - 8:00 PM PST"   # Social media prime time
        else:
            return "12:00 PM - 2:00 PM PST"  # General lunch break

    def _generate_insights(self, features: Dict[str, float], persona_data: Dict,
                          platform: str, engagement: EngagementPrediction) -> List[ContentInsight]:
        """Generate actionable insights from content analysis"""

        insights = []

        # Engagement insights
        if features.get('has_question', 0) == 0:
            insights.append(ContentInsight(
                insight_type="engagement_missing",
                description="Content lacks questions which typically increase engagement",
                confidence=0.8,
                actionable_recommendation="Add a rhetorical question or direct question to encourage responses",
                expected_improvement=0.3
            ))

        if features.get('has_emoji', 0) == 0 and platform in ['twitter', 'threads']:
            insights.append(ContentInsight(
                insight_type="visual_engagement",
                description="Missing emojis that increase visual appeal and emotional connection",
                confidence=0.7,
                actionable_recommendation="Add 1-2 relevant emojis to enhance emotional impact",
                expected_improvement=0.2
            ))

        # Length optimization
        if platform == 'twitter' and features.get('length', 0) < 100:
            insights.append(ContentInsight(
                insight_type="content_length",
                description="Content is quite short for Twitter optimal performance",
                confidence=0.6,
                actionable_recommendation="Expand content with more detail or additional value points",
                expected_improvement=0.15
            ))

        # Authority and credibility
        if features.get('authority_score', 0) < 0.1 and platform == 'linkedin':
            insights.append(ContentInsight(
                insight_type="credibility_boost",
                description="LinkedIn content benefits from authority indicators",
                confidence=0.8,
                actionable_recommendation="Include data, research findings, or expert insights",
                expected_improvement=0.25
            ))

        # Call to action
        if features.get('cta_strength', 0) < 0.2:
            insights.append(ContentInsight(
                insight_type="action_missing",
                description="Content lacks clear call-to-action",
                confidence=0.7,
                actionable_recommendation="Add a specific next step or engagement prompt",
                expected_improvement=0.2
            ))

        # Viral potential insights
        if engagement.viral_potential > 0.7:
            insights.append(ContentInsight(
                insight_type="viral_ready",
                description="Content shows strong viral potential indicators",
                confidence=engagement.confidence_score,
                actionable_recommendation="Consider boosting this content or timing publication carefully",
                expected_improvement=0.5
            ))

        return insights

    def _calculate_viral_potential(self, features: Dict[str, float], engagement: EngagementPrediction) -> float:
        """Calculate viral potential score"""

        viral_factors = {
            'storytelling_score': features.get('storytelling_score', 0) * 0.3,
            'emotional_impact': (features.get('positive_sentiment', 0) + features.get('negative_sentiment', 0)) * 0.2,
            'engagement_hooks': (features.get('has_question', 0) + features.get('cta_strength', 0)) * 0.2,
            'shareability': features.get('urgency_score', 0) * 0.15,
            'authenticity': 0.8,  # Simplified authenticity score
            'timing_factor': 0.7   # Simplified timing factor
        }

        # Weighted sum of viral factors
        viral_score = sum(viral_factors.values())

        # Adjust based on predicted engagement
        engagement_factor = min(1.0, (engagement.predicted_likes + engagement.predicted_shares) / 10.0)

        return min(0.95, viral_score * 0.7 + engagement_factor * 0.3)

    def _recommend_optimizations(self, features: Dict[str, float], insights: List[ContentInsight],
                                platform: str) -> List[Dict[str, Any]]:
        """Generate specific optimization recommendations"""

        optimizations = []

        # Process insights into actionable optimizations
        for insight in insights:
            if insight.insight_type == "engagement_missing":
                optimizations.append({
                    'type': 'add_question',
                    'description': 'Add engagement question',
                    'examples': [
                        'What are your thoughts on this?',
                        'Have you experienced something similar?',
                        'How would you approach this?'
                    ],
                    'priority': 'high',
                    'expected_impact': insight.expected_improvement
                })

            elif insight.insight_type == "visual_engagement":
                optimizations.append({
                    'type': 'add_emojis',
                    'description': 'Add relevant emojis',
                    'examples': ['🚀', '💡', '🎯', '🔥', '✨'],
                    'priority': 'medium',
                    'expected_impact': insight.expected_improvement
                })

            elif insight.insight_type == "credibility_boost":
                optimizations.append({
                    'type': 'add_authority',
                    'description': 'Add credibility indicators',
                    'examples': [
                        'Research shows...',
                        'According to our data...',
                        'In my experience as...',
                        'Studies indicate...'
                    ],
                    'priority': 'high',
                    'expected_impact': insight.expected_improvement
                })

        # Platform-specific optimizations
        if platform == 'twitter' and features.get('length', 0) > 250:
            optimizations.append({
                'type': 'shorten_content',
                'description': 'Condense for Twitter',
                'examples': ['Remove filler words', 'Use shorter sentences', 'Focus on key message'],
                'priority': 'medium',
                'expected_impact': 0.15
            })

        if platform == 'linkedin' and features.get('professional_language', 0) < 0.1:
            optimizations.append({
                'type': 'professionalize_tone',
                'description': 'Make more professional for LinkedIn',
                'examples': ['Use industry terminology', 'Add business context', 'Include professional insights'],
                'priority': 'high',
                'expected_impact': 0.25
            })

        return optimizations

    def _store_performance_data(self, persona_id: str, platform: str,
                               features: Dict[str, float], engagement: EngagementPrediction):
        """Store performance data for continuous learning"""

        performance_record = {
            'timestamp': datetime.now().isoformat(),
            'platform': platform,
            'features': features,
            'engagement_score': (engagement.predicted_likes + engagement.predicted_shares +
                               engagement.predicted_comments) / 3.0,
            'viral_potential': engagement.viral_potential
        }

        self.persona_performance_history[persona_id].append(performance_record)

        # Keep only last 50 records to avoid memory issues
        if len(self.persona_performance_history[persona_id]) > 50:
            self.persona_performance_history[persona_id] = self.persona_performance_history[persona_id][-50:]

    def _calculate_confidence(self, features: Dict[str, float], historical_data: Optional[List] = None) -> float:
        """Calculate confidence in predictions"""

        # Base confidence from feature completeness
        feature_confidence = min(0.9, len([f for f in features.values() if f > 0]) / len(features))

        # Historical data confidence boost
        historical_confidence = 0.0
        if historical_data and len(historical_data) > 5:
            # More historical data = higher confidence
            historical_confidence = min(0.3, len(historical_data) / 100.0)

        return min(0.95, feature_confidence + historical_confidence)

    def _fallback_analysis(self, content: str, platform: str) -> Dict[str, Any]:
        """Fallback analysis when main analysis fails"""

        return {
            'engagement_prediction': EngagementPrediction(
                predicted_likes=2.0,
                predicted_shares=0.5,
                predicted_comments=0.2,
                confidence_score=0.3,
                viral_potential=0.2,
                optimal_posting_time="12:00 PM - 2:00 PM PST"
            ),
            'viral_potential': 0.2,
            'content_insights': [ContentInsight(
                insight_type="fallback",
                description="Limited analysis available",
                confidence=0.3,
                actionable_recommendation="Continue testing different content styles",
                expected_improvement=0.1
            )],
            'optimization_recommendations': [],
            'feature_analysis': {'length': len(content)},
            'confidence_score': 0.3
        }