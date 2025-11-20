#!/usr/bin/env python3
"""
Dynamic Rewriter - Frontend-Integrated Persona Content System

Core Philosophy:
- Dynamic persona creation from frontend uploads
- Real-time voice analysis and pattern extraction
- Adaptive prompt generation based on learned patterns
- Complete frontend-backend integration
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

try:
    from .rag_system import ExampleVectorDatabase
except ImportError:
    # Handle direct script execution
    from rag_system import ExampleVectorDatabase

try:
    from .ab_testing import ABTestingEngine, TestType, VariantType
except ImportError:
    # Handle direct script execution
    from ab_testing import ABTestingEngine, TestType, VariantType

try:
    from .ml_insights import ContentAnalyzer, EngagementPrediction, ContentInsight
except ImportError:
    # Handle direct script execution
    from ml_insights import ContentAnalyzer, EngagementPrediction, ContentInsight

try:
    from .advanced_quality_scorer import AdvancedQualityScorer
except ImportError:
    # Handle direct script execution
    from advanced_quality_scorer import AdvancedQualityScorer

try:
    from .batch_processor import BatchProcessor
except ImportError:
    # Handle direct script execution
    from batch_processor import BatchProcessor

logger = logging.getLogger(__name__)

# Optional sentence_transformers import with graceful fallback
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ SentenceTransformers not available due to dependency conflict: {e}")
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class VoicePatternAnalyzer:
    """Analyze voice patterns from uploaded examples"""

    def __init__(self):
        if SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ VoicePatternAnalyzer initialized with embedding model")
            except Exception as e:
                logger.warning(f"⚠️ Could not load embedding model: {e}")
                self.embedding_model = None
        else:
            logger.warning("⚠️ SentenceTransformers not available - using fallback analysis")
            self.embedding_model = None

    def extract_patterns(self, examples: List[str]) -> Dict[str, Any]:
        """
        Extract comprehensive voice patterns from example posts
        """
        if not examples:
            return self._default_patterns()

        patterns = {
            'sentence_structure': self._analyze_sentence_structure(examples),
            'vocabulary_profile': self._analyze_vocabulary(examples),
            'emotional_markers': self._analyze_emotional_patterns(examples),
            'language_mixing': self._detect_language_mixing(examples),
            'content_focus': self._analyze_content_focus(examples),
            'engagement_patterns': self._analyze_engagement_patterns(examples),
            'authenticity_signals': self._detect_authenticity_signals(examples)
        }

        # Add statistical analysis
        patterns['statistics'] = self._calculate_statistics(examples)
        patterns['voice_embedding'] = self._create_voice_embedding(examples)

        return patterns

    def _analyze_sentence_structure(self, examples: List[str]) -> Dict[str, Any]:
        """Analyze sentence length, complexity, and structure preferences"""
        sentence_lengths = []
        has_questions = 0
        has_exclamations = 0

        for example in examples:
            sentences = [s.strip() for s in example.split('.') if s.strip()]
            for sentence in sentences:
                length = len(sentence)
                sentence_lengths.append(length)

                if '?' in sentence:
                    has_questions += 1
                if '!' in sentence:
                    has_exclamations += 1

        return {
            'avg_sentence_length': np.mean(sentence_lengths) if sentence_lengths else 50,
            'sentence_length_variance': np.var(sentence_lengths) if len(sentence_lengths) > 1 else 0,
            'question_frequency': has_questions / len(examples),
            'exclamation_frequency': has_exclamations / len(examples),
            'complexity_score': self._calculate_complexity_score(examples)
        }

    def _analyze_vocabulary(self, examples: List[str]) -> Dict[str, Any]:
        """Analyze vocabulary patterns and word choices"""
        all_words = []
        technical_terms = []
        casual_terms = []
        emotional_words = []

        # Common vocabulary categories
        tech_words = ['api', 'algorithm', 'code', 'tool', 'software', 'system', 'tech', 'фича', 'баг']
        casual_words = ['awesome', 'cool', 'shit', 'fuck', 'hell', 'damn', 'офигенно', 'зацените', 'блин']
        emotional_words = ['love', 'hate', 'feel', 'felt', 'excited', 'worried', 'нравится', 'ненавижу']

        for example in examples:
            example_lower = example.lower()
            words = example.split()
            all_words.extend(words)

            for word in words:
                if any(tech in word for tech in tech_words):
                    technical_terms.append(word)
                if any(casual in word for casual in casual_words):
                    casual_terms.append(word)
                if any(emotion in word for emotion in emotional_words):
                    emotional_words.append(word)

        return {
            'technical_density': len(technical_terms) / len(all_words) if all_words else 0,
            'casual_density': len(casual_terms) / len(all_words) if all_words else 0,
            'emotional_density': len(emotional_words) / len(all_words) if all_words else 0,
            'unique_words': len(set(all_words)),
            'avg_word_length': np.mean([len(w) for w in all_words]) if all_words else 5,
            'frequent_technical': self._get_top_words(technical_terms, 5),
            'frequent_casual': self._get_top_words(casual_terms, 5),
            'frequent_emotional': self._get_top_words(emotional_words, 5)
        }

    def _analyze_emotional_patterns(self, examples: List[str]) -> Dict[str, Any]:
        """Analyze emotional expression patterns"""
        positive_indicators = ['love', 'amazing', 'awesome', 'excellent', 'great', 'отлично', 'круто', 'люблю']
        negative_indicators = ['hate', 'terrible', 'awful', 'bad', 'ужасно', 'ненавижу', 'проблема']
        neutral_indicators = ['interesting', 'noted', 'observation', 'интересно', 'замечал']

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for example in examples:
            example_lower = example.lower()
            for indicator in positive_indicators:
                positive_count += example_lower.count(indicator)
            for indicator in negative_indicators:
                negative_count += example_lower.count(indicator)
            for indicator in neutral_indicators:
                neutral_count += example_lower.count(indicator)

        total_indicators = positive_count + negative_count + neutral_count

        return {
            'sentiment_distribution': {
                'positive': positive_count / max(total_indicators, 1),
                'negative': negative_count / max(total_indicators, 1),
                'neutral': neutral_count / max(total_indicators, 1)
            },
            'emotional_intensity': (positive_count + negative_count) / max(len(examples), 1),
            'emotional_diversity': len(set([positive_count, negative_count, neutral_count]))
        }

    def _detect_language_mixing(self, examples: List[str]) -> Dict[str, Any]:
        """Detect code-switching and language mixing patterns"""
        russian_chars = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
        english_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

        mixed_posts = 0
        russian_dominant = 0
        english_dominant = 0

        for example in examples:
            russian_count = sum(1 for char in example if char in russian_chars)
            english_count = sum(1 for char in example if char in english_chars)
            total_chars = russian_count + english_count

            if total_chars > 10:  # Avoid counting very short posts
                russian_ratio = russian_count / total_chars
                english_ratio = english_count / total_chars

                if russian_ratio > 0.1 and english_ratio > 0.1:
                    mixed_posts += 1
                elif russian_ratio > english_ratio:
                    russian_dominant += 1
                else:
                    english_dominant += 1

        total = len(examples)

        return {
            'mixing_frequency': mixed_posts / total if total > 0 else 0,
            'language_distribution': {
                'russian_dominant': russian_dominant / total if total > 0 else 0,
                'english_dominant': english_dominant / total if total > 0 else 0,
                'mixed': mixed_posts / total if total > 0 else 0
            },
            'natural_switching': mixed_posts > 0
        }

    def _analyze_content_focus(self, examples: List[str]) -> Dict[str, Any]:
        """Analyze what topics and themes the persona focuses on"""
        topic_keywords = {
            'technology': ['tech', 'code', 'software', 'api', 'algorithm', 'development', 'программирование'],
            'business': ['startup', 'business', 'revenue', 'growth', 'funding', 'бизнес', 'стартап'],
            'personal': ['i', 'my', 'me', 'personally', 'я', 'мой', 'лично'],
            'analysis': ['analysis', 'research', 'data', 'study', 'анализ', 'исследование'],
            'opinion': ['think', 'believe', 'opinion', 'position', 'думаю', 'считаю', 'мнение']
        }

        topic_scores = {}
        for topic, keywords in topic_keywords.items():
            score = 0
            for example in examples:
                example_lower = example.lower()
                for keyword in keywords:
                    score += example_lower.count(keyword)
            topic_scores[topic] = score

        # Normalize scores
        max_score = max(topic_scores.values()) if topic_scores.values() else 1
        topic_focus = {topic: score/max_score for topic, score in topic_scores.items()}

        return {
            'primary_focus': max(topic_focus, key=topic_focus.get),
            'topic_distribution': topic_focus,
            'diversity_score': len([v for v in topic_focus.values() if v > 0.1]) / len(topic_focus)
        }

    def _analyze_engagement_patterns(self, examples: List[str]) -> Dict[str, Any]:
        """Analyze patterns that drive engagement"""
        hooks = 0
        questions = 0
        calls_to_action = 0

        hook_patterns = [
            r'^just.*', r'^guess.*', r'^you won\'t.*', r'^here\'s.*',
            r'^представьте.*', r'^вы не поверите.*', r'^только что.*'
        ]

        question_patterns = [r'\?', r'what.*\?', r'how.*\?', r'когда.*\?', r'как.*\?']

        cta_patterns = [
            r'try.*', r'check.*', r'share.*', r'follow.*',
            r'попробуйте.*', r'проверьте.*', r'поделитесь.*'
        ]

        for example in examples:
            example_lower = example.lower()
            # Check hooks
            for pattern in hook_patterns:
                if re.search(pattern, example_lower):
                    hooks += 1
                    break

            # Check questions
            for pattern in question_patterns:
                if re.search(pattern, example_lower):
                    questions += 1
                    break

            # Check CTAs
            for pattern in cta_patterns:
                if re.search(pattern, example_lower):
                    calls_to_action += 1
                    break

        return {
            'hook_usage': hooks / len(examples),
            'question_usage': questions / len(examples),
            'cta_usage': calls_to_action / len(examples),
            'engagement_optimization': (hooks + questions + calls_to_action) / len(examples)
        }

    def _detect_authenticity_signals(self, examples: List[str]) -> Dict[str, Any]:
        """Detect signals that indicate authentic human writing"""
        authenticity_signals = {
            'personal_experiences': 0,
            'specific_details': 0,
            'imperfections': 0,
            'vulnerability': 0
        }

        personal_indicators = ['i tried', 'i tested', 'i used', 'i found', 'я пробовал', 'я тестировал']
        specific_indicators = [r'\d+', r'\$[\d,]+', r'\d+%', r'\d+\.\d+']
        vulnerability_indicators = ['struggle', 'challenge', 'difficult', 'worried', 'борьба', 'сложно']

        for example in examples:
            example_lower = example.lower()
            # Personal experiences
            for indicator in personal_indicators:
                authenticity_signals['personal_experiences'] += example_lower.count(indicator)

            # Specific details (numbers, prices, percentages)
            for pattern in specific_indicators:
                matches = re.findall(pattern, example)
                authenticity_signals['specific_details'] += len(matches)

            # Vulnerability
            for indicator in vulnerability_indicators:
                authenticity_signals['vulnerability'] += example_lower.count(indicator)

            # Imperfections (slight typos, casual language)
            if any(word in example_lower for word in ['tho', 'kinda', 'sorta', 'немного', 'чуть']):
                authenticity_signals['imperfections'] += 1

        # Normalize per example
        for key in authenticity_signals:
            authenticity_signals[key] = authenticity_signals[key] / len(examples)

        return authenticity_signals

    def _calculate_statistics(self, examples: List[str]) -> Dict[str, Any]:
        """Calculate basic statistics about the examples"""
        lengths = [len(example) for example in examples]
        word_counts = [len(example.split()) for example in examples]

        return {
            'total_examples': len(examples),
            'avg_length': np.mean(lengths) if lengths else 0,
            'length_variance': np.var(lengths) if len(lengths) > 1 else 0,
            'avg_word_count': np.mean(word_counts) if word_counts else 0,
            'total_words': sum(word_counts)
        }

    def _create_voice_embedding(self, examples: List[str]) -> Optional[List[float]]:
        """Create embedding representing the voice"""
        if not self.embedding_model or not examples:
            return None

        try:
            # Combine all examples into one text for embedding
            combined_text = " ".join(examples)
            embedding = self.embedding_model.encode(combined_text)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"Could not create voice embedding: {e}")
            return None

    def _calculate_complexity_score(self, examples: List[str]) -> float:
        """Calculate linguistic complexity score"""
        total_complexity = 0

        for example in examples:
            # Simple complexity metrics
            avg_word_length = np.mean([len(word) for word in example.split()]) if example.split() else 0
            sentence_count = len([s for s in example.split('.') if s.strip()])
            complexity = avg_word_length * 0.3 + sentence_count * 0.2
            total_complexity += complexity

        return total_complexity / len(examples) if examples else 0

    def _get_top_words(self, words: List[str], limit: int) -> List[str]:
        """Get most frequent words"""
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        return sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:limit]

    def _default_patterns(self) -> Dict[str, Any]:
        """Default patterns when no examples available"""
        return {
            'sentence_structure': {'avg_sentence_length': 50, 'complexity_score': 0.5},
            'vocabulary_profile': {'technical_density': 0.1, 'casual_density': 0.1},
            'emotional_markers': {'sentiment_distribution': {'positive': 0.3, 'negative': 0.1, 'neutral': 0.6}},
            'language_mixing': {'mixing_frequency': 0.0, 'natural_switching': False},
            'content_focus': {'primary_focus': 'general', 'diversity_score': 0.2},
            'engagement_patterns': {'engagement_optimization': 0.1},
            'authenticity_signals': {'personal_experiences': 0.1, 'specific_details': 0.1},
            'statistics': {'total_examples': 0},
            'voice_embedding': None
        }


class DynamicPromptGenerator:
    """Generate dynamic prompts based on analyzed voice patterns"""

    def __init__(self):
        self.voice_analyzer = VoicePatternAnalyzer()
        logger.info("✅ DynamicPromptGenerator initialized")

    def create_persona_strategy(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Create persona-specific prompt strategy from voice patterns"""
        strategy = {
            'core_identity': self._create_identity(patterns),
            'voice_guidelines': self._create_voice_guidelines(patterns),
            'structure_preferences': self._create_structure_guidelines(patterns),
            'content_guidelines': self._create_content_guidelines(patterns),
            'engagement_strategies': self._create_engagement_strategies(patterns),
            'negative_constraints': self._create_negative_constraints(patterns)
        }

        return strategy

    def _create_identity(self, patterns: Dict[str, Any]) -> str:
        """Create core identity statement"""
        content_focus = patterns.get('content_focus', {})
        primary_focus = content_focus.get('primary_focus', 'general')

        language_mixing = patterns.get('language_mixing', {})
        mixing_freq = language_mixing.get('mixing_frequency', 0)

        identity_templates = {
            'technology': "I'm a tech professional who shares honest opinions about tools and trends",
            'business': "I'm a business builder sharing practical insights about startups and growth",
            'personal': "I'm someone who shares personal experiences and reflections",
            'general': "I'm someone who shares observations and insights"
        }

        base_identity = identity_templates.get(primary_focus, identity_templates['general'])

        # Add language mixing information
        if mixing_freq > 0.3:
            base_identity += ". I naturally mix languages like many bilingual people do"

        return base_identity

    def _create_voice_guidelines(self, patterns: Dict[str, Any]) -> List[str]:
        """Create voice-specific guidelines"""
        guidelines = []

        vocabulary = patterns.get('vocabulary_profile', {})
        tech_density = vocabulary.get('technical_density', 0)
        casual_density = vocabulary.get('casual_density', 0)

        # Technical language guidelines
        if tech_density > 0.2:
            guidelines.append("Use technical terms naturally when they add value")
        elif tech_density > 0.1:
            guidelines.append("Include some technical details but keep them accessible")
        else:
            guidelines.append("Keep language simple and accessible")

        # Casual language guidelines
        if casual_density > 0.1:
            guidelines.append("Use casual language and slang naturally")
        else:
            guidelines.append("Maintain professional but approachable tone")

        # Sentence structure guidelines
        sentence_structure = patterns.get('sentence_structure', {})
        avg_length = sentence_structure.get('avg_sentence_length', 50)

        if avg_length < 30:
            guidelines.append("Use short, punchy sentences")
        elif avg_length > 70:
            guidelines.append("Use longer, more complex sentences")
        else:
            guidelines.append("Vary sentence length for natural flow")

        return guidelines

    def _create_structure_guidelines(self, patterns: Dict[str, Any]) -> List[str]:
        """Create content structure guidelines"""
        guidelines = []

        engagement = patterns.get('engagement_patterns', {})
        hook_usage = engagement.get('hook_usage', 0)
        question_usage = engagement.get('question_usage', 0)

        if hook_usage > 0.3:
            guidelines.append("Start with a strong hook to grab attention")

        if question_usage > 0.3:
            guidelines.append("Include questions to encourage engagement")

        # Language mixing structure
        language_mixing = patterns.get('language_mixing', {})
        if language_mixing.get('natural_switching', False):
            guidelines.append("Switch languages naturally when it feels authentic")

        return guidelines

    def _create_content_guidelines(self, patterns: Dict[str, Any]) -> List[str]:
        """Create content-specific guidelines"""
        guidelines = []

        authenticity = patterns.get('authenticity_signals', {})
        personal_exp = authenticity.get('personal_experiences', 0)
        specific_details = authenticity.get('specific_details', 0)

        if personal_exp > 0.2:
            guidelines.append("Write from personal experience - use 'I tried', 'I noticed', 'I tested'")

        if specific_details > 0.1:
            guidelines.append("Include specific details, numbers, and concrete examples")

        return guidelines

    def _create_engagement_strategies(self, patterns: Dict[str, Any]) -> List[str]:
        """Create engagement-focused strategies"""
        strategies = []

        emotional = patterns.get('emotional_markers', {})
        sentiment_dist = emotional.get('sentiment_distribution', {})
        positive_ratio = sentiment_dist.get('positive', 0.3)

        if positive_ratio > 0.4:
            strategies.append("Maintain positive, optimistic tone")
        elif positive_ratio < 0.2:
            strategies.append("Express critical or skeptical viewpoints")
        else:
            strategies.append("Balance optimism with realistic assessment")

        return strategies

    def _create_negative_constraints(self, patterns: Dict[str, Any]) -> List[str]:
        """Create things to avoid"""
        constraints = []

        # Based on analysis, add constraints
        constraints.append("Avoid AI-like filler phrases")
        constraints.append("Don't use hashtags or emojis (personal account style)")
        constraints.append("Avoid corporate speak or marketing language")

        return constraints

    def generate_prompt(self, strategy: Dict[str, Any], content: Dict[str, Any], platform: str, examples: List[str]) -> str:
        """Generate dynamic prompt based on strategy and content"""

        # Extract key content information
        topic = content.get('topic', content.get('content', ''))[:200]
        category = content.get('category', 'interesting topic')

        # Select most relevant examples (up to 3)
        relevant_examples = examples[:3] if examples else []

        # Build prompt sections
        prompt_parts = []

        # 1. Identity section
        prompt_parts.append(strategy['core_identity'])

        # 2. Situation context
        prompt_parts.append("")
        prompt_parts.append("Here's what just happened:")
        prompt_parts.append(f"Topic: {topic}")
        if category != 'general':
            prompt_parts.append(f"This feels like {category} content.")

        # 3. Voice examples (if available)
        if relevant_examples:
            prompt_parts.append("")
            prompt_parts.append("Here are some things I've said before that feel similar:")
            for example in relevant_examples:
                prompt_parts.append(f"- {example}")

        # 4. Voice guidelines (convert to natural instructions)
        if strategy['voice_guidelines']:
            prompt_parts.append("")
            prompt_parts.append("How I naturally write:")
            for guideline in strategy['voice_guidelines'][:3]:  # Limit to top 3
                prompt_parts.append(f"- {guideline}")

        # 5. Platform and personality-aware instructions
        personality_instructions = self._get_personality_instructions(strategy)

        platform_guidance = {
            'twitter': {
                'base': "Write a single tweet (max 280 characters). Start with an engaging hook that grabs attention immediately. Use a conversational tone.",
                'tech_founder': "Use an energetic startup tone! Start with excitement about the tech/innovation. Include 1-2 relevant emojis naturally. Ask engaging questions like 'What do you think?' or 'Has anyone else tried this?' Use phrases like 'Game changer!' or 'Mind blown!'.",
                'academic_researcher': "Lead with a surprising insight or finding. Ask thought-provoking questions to engage the audience. Use precise language but make it accessible. Include phrases like 'The data suggests...' or 'This research shows...'",
                'marketing_influencer': "Go ALL IN with energy! Start with excitement using 🔥 or ✨. Use questions like 'Are you ready for this?' or 'Who else is excited?'. Use hype phrases like 'This is HUGE!' or 'You need to see this!'. Multiple enthusiastic emojis if natural.",
                'casual_professional': "Start with a relatable observation or question. Use a balanced tone with thoughtful engagement. Ask questions like 'What's your take?' or 'Anyone else experienced this?'. Use 1-2 subtle emojis if it fits your style."
            },
            'linkedin': {
                'base': "Write a LinkedIn post (2-3 paragraphs max). Start with a professional hook that provides immediate value or insight. Use a personal yet authoritative tone.",
                'tech_founder': "Lead with a business insight or industry trend. Share a forward-looking perspective on what this means for the industry. Use phrases like 'The future of...' or 'Here's what I'm seeing...'. End with a strategic question to engage professionals.",
                'academic_researcher': "Open with a research finding or methodological insight. Explain the business or practical implications. Use phrases like 'Our research indicates...' or 'The implications are significant...'. Invite professional discussion with thoughtful questions.",
                'marketing_influencer': "Start with a valuable insight or trend observation. Share expertise with energy while maintaining professional standards. Use phrases like 'Here's what's working...' or 'The opportunity is massive...'. End with an engaging call to discussion.",
                'casual_professional': "Begin with a personal experience or observation that connects to broader business insights. Share lessons learned or perspectives. Use phrases like 'Something I've been thinking about...' or 'From my experience...'. Invite others to share their perspectives."
            },
            'threads': {
                'base': "Write a Threads post (max 500 characters). Be very conversational and authentic. Start with a natural, spontaneous thought or question.",
                'tech_founder': "Share excitement about new tech or innovations in a casual way. Start with spontaneous thoughts like 'Okay, this is cool...' or 'Just tried...'. Use conversational questions and natural energy. 2-3 emojis if it feels authentic.",
                'academic_researcher': "Make complex ideas accessible through casual explanation. Start with 'Mind-blowing fact:' or 'Something fascinating...'. Break down concepts in simple terms. Ask engaging questions that make people think.",
                'marketing_influencer': "Be extremely casual and relatable! Start with 'OMG you guys...' or 'Wait until you hear this...'. Use lots of energy, emojis, and conversational questions. Make it feel like sharing exciting news with friends.",
                'casual_professional': "Share insights in a friendly, approachable way. Start with 'Something interesting I've been thinking about...' or 'Quick thought...'. Use natural language and invite casual discussion."
            },
            'telegram': {
                'base': "Write a Telegram message with more depth than Twitter. Start with context that provides value to the community.",
                'tech_founder': "Share detailed tech insights with business context. Start with 'Big news in tech...' or 'Just came across this...'. Provide thorough analysis and forward-looking perspectives. Ask engaging questions for the tech community.",
                'academic_researcher': "Share research findings with appropriate depth and context. Start with 'Important research update...' or 'New findings suggest...'. Include methodology and implications. Invite thoughtful discussion from the community.",
                'marketing_influencer': "Share discoveries with excitement and comprehensive detail. Start with 'You need to see this...' or 'Game-changing update...'. Provide valuable insights and context. End with engaging questions to spark discussion.",
                'casual_professional': "Share thoughtful insights with valuable context for the community. Start with 'Something worth discussing...' or 'Important perspective...'. Provide analysis that helps others understand the bigger picture."
            }
        }

        # Enhanced format constraints with personality adaptation
        format_rules = [
            "IMPORTANT: Give me ONLY the final content - no options, no explanations, no 'here are some choices'",
            f"Write as if you're actually posting this yourself right now",
            f"Match the personality style: {personality_instructions.get('style_description', 'authentic and engaging')}",
            f"Use these engagement elements: {personality_instructions.get('engagement_style', 'be natural and engaging')}",
            f"Match the length and style constraints for the platform"
        ]

        platform_config = platform_guidance.get(platform, {'base': "Write a single post for this platform."})
        base_instruction = platform_config.get('base', platform_config['base'])

        # Get personality-specific platform instruction
        detected_personality = getattr(self, '_current_personality_type', 'custom')
        personality_specific = platform_config.get(detected_personality, base_instruction)

        prompt_parts.append("")
        prompt_parts.append(base_instruction)
        if detected_personality in platform_config and detected_personality != 'custom':
            prompt_parts.append(f"Personality Style: {personality_specific}")
        prompt_parts.append("")
        prompt_parts.extend(format_rules)

        return "\n".join(prompt_parts)

    def _get_personality_instructions(self, strategy: Dict[str, Any]) -> Dict[str, str]:
        """Get personality-specific instructions based on detected personality type"""
        detected_personality = getattr(self, '_current_personality_type', 'custom')

        personality_guides = {
            'tech_founder': {
                'style_description': 'energetic startup founder building the future',
                'engagement_style': 'use business language, growth metrics, occasional emojis (🚀💡), and exclamation points'
            },
            'academic_researcher': {
                'style_description': 'analytical researcher sharing insights',
                'engagement_style': 'use precise language, evidence-based claims, thoughtful questions, minimal emojis (📊🔬)'
            },
            'marketing_influencer': {
                'style_description': 'enthusiastic influencer sharing discoveries',
                'engagement_style': 'use high energy, multiple emojis (🔥✨💖), exclamation points, exciting language, and engagement questions'
            },
            'casual_professional': {
                'style_description': 'thoughtful professional sharing insights',
                'engagement_style': 'use balanced tone, occasional emojis (✅👍), thoughtful questions, and clear value propositions'
            },
            'custom': {
                'style_description': 'authentic personal voice',
                'engagement_style': 'be natural and engaging based on your examples'
            }
        }

        return personality_guides.get(detected_personality, personality_guides['custom'])


class PersonalityDetector:
    """Detect personality types from text examples"""

    def __init__(self):
        self.personality_signatures = self._initialize_signatures()

    def _initialize_signatures(self):
        return {
            'tech_founder': {
                'lexical_markers': [
                    'raised', 'funding', 'seed', 'round', 'hiring', 'culture',
                    'building', 'startup', 'ship', 'iterate', 'lean', 'methodology',
                    'future', 'disrupt', 'innovate', 'scale', 'growth', 'ecosystem',
                    'traction', 'product', 'launch', 'pivot', 'revenue'
                ],
                'structural_markers': {
                    'avg_sentence_length': (12, 18),
                    'exclamation_freq': (0.05, 0.15),
                    'question_freq': (0.05, 0.12)
                },
                'emoji_patterns': ['🚀', '💡', '🎯', '📈'],
                'tone_indicators': ['building', 'scaling', 'disrupting', 'revolutionizing'],
                'weight': 1.0
            },
            'academic_researcher': {
                'lexical_markers': [
                    'paper', 'research', 'study', 'analysis', 'findings', 'results',
                    'correlation', 'implications', 'methodology', 'peer review',
                    'conference', 'journal', 'accepted', 'algorithm', 'model',
                    'framework', 'hypothesis', 'significant', 'statistical'
                ],
                'structural_markers': {
                    'avg_sentence_length': (18, 25),
                    'exclamation_freq': (0.0, 0.08),
                    'question_freq': (0.0, 0.1)
                },
                'emoji_patterns': ['📊', '🔬', '📚', '🧪'],
                'tone_indicators': ['findings suggest', 'results indicate', 'further research', 'methodology'],
                'weight': 1.0
            },
            'marketing_influencer': {
                'lexical_markers': [
                    'alert', 'pro', 'secret', 'exclusive', 'limited', 'amazing',
                    'incredible', 'mind blown', 'obsessed', 'literally', 'actually',
                    'game changer', 'life changing', 'you guys', 'link in bio',
                    'check this out', 'unbelievable', 'insane'
                ],
                'structural_markers': {
                    'avg_sentence_length': (8, 15),
                    'exclamation_freq': (0.25, 0.5),
                    'question_freq': (0.1, 0.3)
                },
                'emoji_patterns': ['🔥', '✨', '💖', '🎨', '🤯', '💯', '👑'],
                'tone_indicators': ['omg', 'literally', 'can\'t believe', 'so excited'],
                'weight': 1.0
            },
            'casual_professional': {
                'lexical_markers': [
                    'working on', 'thoughts on', 'interesting', 'excited about',
                    'looking forward', 'great discussion', 'thanks for sharing',
                    'definitely', 'absolutely', 'personally', 'experience'
                ],
                'structural_markers': {
                    'avg_sentence_length': (15, 20),
                    'exclamation_freq': (0.08, 0.2),
                    'question_freq': (0.05, 0.15)
                },
                'emoji_patterns': ['👍', '😊', '💭', '✅'],
                'tone_indicators': ['personally', 'excited', 'interesting', 'thoughts'],
                'weight': 0.7  # Lower weight as it's more generic
            }
        }

    def detect_personality_type(self, examples: List[str]) -> Dict[str, float]:
        """Detect personality type with confidence scores"""
        if not examples:
            return {'custom': 1.0}

        combined_text = " ".join(examples).lower()
        scores = {}

        for personality, signature in self.personality_signatures.items():
            scores[personality] = self._calculate_match_score(examples, combined_text, signature)

        # Normalize scores
        total_score = sum(scores.values())
        if total_score > 0:
            scores = {k: v / total_score for k, v in scores.items()}
        else:
            scores = {'custom': 1.0}

        return scores

    def _calculate_match_score(self, examples: List[str], combined_text: str, signature: Dict) -> float:
        """Calculate how well examples match a personality signature"""
        score = 0.0

        # Lexical matching (40% of score)
        lexical_score = 0.0
        for marker in signature['lexical_markers']:
            if marker in combined_text:
                lexical_score += 1
        lexical_score = min(1.0, lexical_score / len(signature['lexical_markers']))
        score += lexical_score * 0.4

        # Structural matching (30% of score)
        structural_score = self._analyze_structural_patterns(examples, signature['structural_markers'])
        score += structural_score * 0.3

        # Emoji patterns (20% of score)
        emoji_score = self._analyze_emoji_patterns(examples, signature['emoji_patterns'])
        score += emoji_score * 0.2

        # Tone indicators (10% of score)
        tone_score = self._analyze_tone_indicators(examples, signature['tone_indicators'])
        score += tone_score * 0.1

        # Apply personality weight
        score *= signature['weight']

        return min(1.0, score)

    def _analyze_structural_patterns(self, examples: List[str], markers: Dict) -> float:
        """Analyze sentence structure patterns"""
        if not examples:
            return 0.0

        # Calculate sentence lengths
        all_sentences = []
        exclamation_count = 0
        question_count = 0

        for example in examples:
            sentences = [s.strip() for s in example.split('.') if s.strip()]
            all_sentences.extend(sentences)
            exclamation_count += example.count('!')
            question_count += example.count('?')

        if not all_sentences:
            return 0.0

        avg_length = np.mean([len(s.split()) for s in all_sentences])
        total_sentences = len(all_sentences)

        # Check average sentence length
        target_range = markers.get('avg_sentence_length', (0, 50))
        length_score = 1.0 if target_range[0] <= avg_length <= target_range[1] else 0.5

        # Check punctuation frequencies
        exclamation_freq = exclamation_count / total_sentences
        question_freq = question_count / total_sentences

        exclamation_score = 1.0 if markers.get('exclamation_freq', (0, 1))[0] <= exclamation_freq <= markers.get('exclamation_freq', (0, 1))[1] else 0.5
        question_score = 1.0 if markers.get('question_freq', (0, 1))[0] <= question_freq <= markers.get('question_freq', (0, 1))[1] else 0.5

        return (length_score + exclamation_score + question_score) / 3

    def _analyze_emoji_patterns(self, examples: List[str], expected_emojis: List[str]) -> float:
        """Analyze emoji usage patterns"""
        if not examples or not expected_emojis:
            return 0.5

        combined_text = " ".join(examples)
        emoji_matches = sum(1 for emoji in expected_emojis if emoji in combined_text)

        return min(1.0, emoji_matches / len(expected_emojis))

    def _analyze_tone_indicators(self, examples: List[str], indicators: List[str]) -> float:
        """Analyze tone-specific language indicators"""
        if not examples or not indicators:
            return 0.5

        combined_text = " ".join(examples).lower()
        indicator_matches = sum(1 for indicator in indicators if indicator in combined_text)

        return min(1.0, indicator_matches / len(indicators))


class DynamicRewriter:
    """Main dynamic rewriter with frontend integration and RAG system"""

    def __init__(self):
        self.voice_analyzer = VoicePatternAnalyzer()
        self.prompt_generator = DynamicPromptGenerator()
        self.personality_detector = PersonalityDetector()
        self._current_personality_type = 'custom'  # Initialize personality type

        # Initialize RAG system if dependencies are available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.vector_db = ExampleVectorDatabase()
                logger.info("✅ Vector database initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize vector database: {e}")
                self.vector_db = None
        else:
            logger.warning("⚠️ RAG system disabled - SentenceTransformers not available")
            self.vector_db = None

        # Initialize A/B testing engine
        self.ab_testing = ABTestingEngine()
        logger.info("✅ A/B testing engine initialized")

        # Initialize ML insights analyzer
        try:
            self.ml_analyzer = ContentAnalyzer()
            logger.info("✅ ML insights analyzer initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize ML analyzer: {e}")
            self.ml_analyzer = None

        # Initialize advanced quality scorer
        try:
            self.quality_scorer = AdvancedQualityScorer()
            logger.info("✅ Advanced quality scorer initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize quality scorer: {e}")
            self.quality_scorer = None

        # Initialize batch processor
        try:
            self.batch_processor = BatchProcessor(self)
            logger.info("✅ Batch processor initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize batch processor: {e}")
            self.batch_processor = None

        # AI Model setup
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        self.gemini_api_keys = self._load_gemini_keys()

        rag_status = "with RAG" if self.vector_db else "without RAG (fallback mode)"
        logger.info(f"✅ DynamicRewriter initialized with frontend integration {rag_status}")

    def _load_gemini_keys(self) -> List[str]:
        """Load Gemini API keys"""
        keys = []

        primary_key = os.getenv("GEMINI_API_KEY")
        if primary_key:
            keys.append(primary_key)

        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if not key:
                break
            keys.append(key)
            i += 1

        return keys

    def create_persona_from_examples(self, examples: List[str], persona_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create persona from frontend-uploaded examples"""
        logger.info(f"🎭 Creating persona from {len(examples)} examples")

        # Analyze voice patterns
        patterns = self.voice_analyzer.extract_patterns(examples)
        logger.info("✅ Voice patterns analyzed")

        # Create prompt strategy
        strategy = self.prompt_generator.create_persona_strategy(patterns)
        logger.info("✅ Prompt strategy created")

        # Store examples in vector database for RAG
        persona_id = persona_info.get('id', f"persona_{datetime.now().timestamp()}")
        try:
            example_ids = self.vector_db.add_examples_batch(
                persona_id=persona_id,
                examples=examples,
                metadata={
                    'persona_name': persona_info.get('name', 'New Persona'),
                    'created_at': datetime.now().isoformat(),
                    'platforms': persona_info.get('platforms', ['twitter'])
                }
            )
            logger.info(f"✅ Stored {len(example_ids)} examples in vector database")
        except Exception as e:
            logger.error(f"⚠️ Failed to store examples in vector database: {e}")

        # Create persona data
        persona_data = {
            'id': persona_id,
            'name': persona_info.get('name', 'New Persona'),
            'handle': persona_info.get('handle', '@newpersona'),
            'description': persona_info.get('description', ''),
            'platforms': persona_info.get('platforms', ['twitter']),
            'patterns': patterns,
            'strategy': strategy,
            'examples': examples,
            'created_at': datetime.now().isoformat(),
            'quality_metrics': {
                'voice_consistency': self._calculate_voice_consistency(patterns),
                'authenticity_prediction': self._predict_authenticity(patterns),
                'engagement_potential': self._predict_engagement(patterns)
            }
        }

        logger.info(f"✅ Persona created: {persona_data['name']} with {len(examples)} examples")
        return persona_data

    def _calculate_voice_consistency(self, patterns: Dict[str, Any]) -> float:
        """Calculate voice consistency score"""
        variance = patterns.get('sentence_structure', {}).get('sentence_length_variance', 0)
        diversity = patterns.get('content_focus', {}).get('diversity_score', 0)

        # Lower variance and moderate diversity indicate consistency
        consistency = max(0, 1.0 - (variance / 1000))  # Normalize variance
        consistency = consistency * (0.7 + 0.3 * diversity)  # Account for diversity

        return min(1.0, consistency)

    def _predict_authenticity(self, patterns: Dict[str, Any]) -> float:
        """Predict authenticity score based on patterns"""
        authenticity_signals = patterns.get('authenticity_signals', {})

        # Weight different authenticity signals
        personal_exp = authenticity_signals.get('personal_experiences', 0)
        specific_details = authenticity_signals.get('specific_details', 0)
        imperfections = authenticity_signals.get('imperfections', 0)

        authenticity_score = (personal_exp * 0.4 + specific_details * 0.4 + imperfections * 0.2)

        # Adjust for other factors
        emotional_naturalness = patterns.get('emotional_markers', {}).get('emotional_intensity', 0)
        engagement_optimization = patterns.get('engagement_patterns', {}).get('engagement_optimization', 0)

        authenticity_score = authenticity_score * 0.8 + emotional_naturalness * 0.1 + engagement_optimization * 0.1

        return min(1.0, authenticity_score)

    def _predict_engagement(self, patterns: Dict[str, Any]) -> float:
        """Predict engagement potential"""
        engagement_patterns = patterns.get('engagement_patterns', {})
        emotional_markers = patterns.get('emotional_markers', {})

        # Combine engagement factors
        engagement_optimization = engagement_patterns.get('engagement_optimization', 0)
        emotional_intensity = emotional_markers.get('emotional_intensity', 0)
        question_frequency = engagement_patterns.get('question_usage', 0)

        engagement_score = (engagement_optimization * 0.4 + emotional_intensity * 0.3 + question_frequency * 0.3)

        return min(1.0, engagement_score)

    async def generate_content(self, persona_data: Dict[str, Any], content: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """Generate content using dynamic persona with RAG-enhanced example retrieval"""
        logger.info(f"📝 Generating content for {persona_data['name']} on {platform}")

        try:
            # Store current persona data for consistency checking
            self._current_persona_data = persona_data

            # Use RAG to find relevant examples for this specific topic
            topic = content.get('topic', '')
            rag_examples = []

            if topic:
                # RAG SYSTEM DISABLED DUE TO DEPENDENCY ISSUE
                # The sentence_transformers library has compatibility issues with newer huggingface_hub
                # TODO: Fix dependency conflicts before re-enabling RAG
                logger.info("⚠️ RAG disabled due to huggingface_hub compatibility issue - using persona examples")
                rag_examples = persona_data['examples'][:3]  # Use persona examples as fallback

                # Keep original RAG code for when dependencies are fixed:
                # try:
                #     # Search vector database for semantically similar examples
                #     search_results = self.vector_db.search_similar(
                #         query=topic,
                #         persona_id=persona_data['id'],
                #         k=3,  # Get top 3 most relevant examples
                #         threshold=0.1
                #     )
                #
                #     rag_examples = [result['content'] for result in search_results]
                #     logger.info(f"🔍 RAG: Found {len(rag_examples)} relevant examples for topic: {topic[:50]}...")
                #
                # except Exception as e:
                #     logger.warning(f"⚠️ RAG search failed: {e}, using original examples")
                #     rag_examples = persona_data['examples'][:3]  # Fallback to original examples
            else:
                rag_examples = persona_data['examples'][:3]  # Use original examples if no topic

            # DETECT PERSONALITY TYPE for enhanced prompts
            personality_scores = self.personality_detector.detect_personality_type(persona_data.get('examples', []))
            dominant_personality = max(personality_scores.items(), key=lambda x: x[1])
            detected_personality = dominant_personality[0] if dominant_personality[1] > 0.25 else 'custom'

            # Store current personality type for prompt generation
            self._current_personality_type = detected_personality
            logger.info(f"🎭 Detected personality: {detected_personality} (confidence: {dominant_personality[1]:.2f})")

            # Generate dynamic prompt with RAG-enhanced examples
            strategy = persona_data.get('strategy', {
                'core_identity': "I'm a professional sharing insights and observations",
                'voice_guidelines': ['Write in a clear, engaging style'],
                'structure_preferences': ['Use clear, concise sentences'],
                'content_guidelines': ['Focus on providing value to the audience'],
                'engagement_strategies': ['Include questions to encourage interaction'],
                'negative_constraints': ['Avoid being overly promotional']
            })

            prompt = self.prompt_generator.generate_prompt(
                strategy,
                content,
                platform,
                rag_examples
            )

            logger.debug(f"Generated prompt with RAG: {len(prompt)} characters")

            # Call AI model
            result = await self._call_ai_model(prompt)

            # Post-process content
            cleaned_content = self._post_process_content(result)

            # Enhanced quality assessment with RAG metrics
            quality_dict = self._assess_quality_with_rag(cleaned_content, persona_data, platform, rag_examples)
            quality_score = quality_dict.get('overall_quality', quality_dict) if isinstance(quality_dict, dict) else quality_dict

            # Include detailed quality metrics
            result_data = {
                'success': True,
                'persona_id': persona_data['id'],
                'persona_name': persona_data['name'],
                'platform': platform,
                'content': cleaned_content,
                'prompt_used': prompt,
                'quality_score': quality_score,
                'length': len(cleaned_content),
                'generated_at': '2024-01-01T00:00:00',  # Fixed timestamp to debug format issue
                'rag_examples_used': len(rag_examples),
                'rag_sources': [{'content': ex, 'relevance': 0.8} for ex in rag_examples] if rag_examples else []
            }

            # Add detailed quality metrics if available
            if isinstance(quality_dict, dict):
                result_data.update({
                    'voice_match': quality_dict.get('voice_consistency', quality_score),  # Keep compatibility with old field name
                    'voice_consistency': quality_dict.get('voice_consistency', quality_score),
                    'authenticity_prediction': quality_dict.get('authenticity_prediction', quality_score),
                    'engagement_potential': quality_dict.get('engagement_potential', quality_score),
                    'topic_relevance': quality_dict.get('topic_relevance', 0.0)
                })

            # Add ML insights if available
            if self.ml_analyzer:
                try:
                    ml_analysis = self.ml_analyzer.analyze_content_performance(
                        cleaned_content, persona_data, platform
                    )

                    # Convert ML dataclasses to dicts for JSON serialization
                    engagement_pred = ml_analysis.get('engagement_prediction')
                    if engagement_pred:
                        result_data.update({
                            'ml_engagement_prediction': {
                                'predicted_likes': engagement_pred.predicted_likes,
                                'predicted_shares': engagement_pred.predicted_shares,
                                'predicted_comments': engagement_pred.predicted_comments,
                                'confidence_score': engagement_pred.confidence_score,
                                'viral_potential': engagement_pred.viral_potential,
                                'optimal_posting_time': engagement_pred.optimal_posting_time
                            },
                            'ml_viral_potential': ml_analysis.get('viral_potential', 0.0),
                            'ml_confidence_score': ml_analysis.get('confidence_score', 0.0)
                        })

                    # Add content insights
                    insights = ml_analysis.get('content_insights', [])
                    if insights:
                        result_data['ml_insights'] = [
                            {
                                'type': insight.insight_type,
                                'description': insight.description,
                                'confidence': insight.confidence,
                                'recommendation': insight.actionable_recommendation,
                                'expected_improvement': insight.expected_improvement
                            }
                            for insight in insights
                        ]

                    # Add optimization recommendations
                    optimizations = ml_analysis.get('optimization_recommendations', [])
                    if optimizations:
                        result_data['ml_optimizations'] = optimizations

                    logger.info(f"🧠 ML insights generated: {len(insights)} insights, {len(optimizations)} optimizations")

                except Exception as e:
                    logger.warning(f"⚠️ ML analysis failed: {e}")

            # Add advanced quality scoring if available
            if self.quality_scorer:
                try:
                    voice_analysis = quality_dict if isinstance(quality_dict, dict) else None
                    advanced_quality = self.quality_scorer.calculate_comprehensive_quality_score(
                        cleaned_content, persona_data, platform, voice_analysis
                    )

                    # Convert engagement prediction to dict
                    engagement_pred = advanced_quality.get('engagement_prediction')
                    if engagement_pred:
                        result_data.update({
                            'advanced_quality_score': advanced_quality['overall_score'],
                            'quality_grade': advanced_quality['grade'],
                            'quality_confidence': advanced_quality['confidence_score'],
                            'quality_dimensions': advanced_quality['dimensions'],
                            'advanced_engagement_prediction': {
                                'predicted_rate': engagement_pred.predicted_engagement_rate,
                                'confidence_interval': engagement_pred.confidence_interval,
                                'key_drivers': engagement_pred.key_drivers,
                                'risk_factors': engagement_pred.risk_factors,
                                'optimization_potential': engagement_pred.optimization_potential
                            },
                            'key_strengths': advanced_quality['key_strengths'],
                            'improvement_areas': advanced_quality['improvement_areas'],
                            'optimization_opportunities': advanced_quality['optimization_opportunities']
                        })

                    logger.info(f"📊 Advanced quality analysis: {advanced_quality['overall_score']:.3f} score ({advanced_quality['grade']} grade)")

                except Exception as e:
                    logger.warning(f"⚠️ Advanced quality scoring failed: {e}")

            logger.info(f"✅ RAG-enhanced content generated: {quality_score:.2f} quality, {len(cleaned_content)} chars, {len(rag_examples)} RAG examples")
            return result_data

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'persona_id': persona_data['id'],
                'platform': platform
            }

    async def _call_ai_model(self, prompt: str) -> str:
        """Call AI model with fallback"""
        if not self.gemini_api_keys:
            raise Exception("No Gemini API keys configured")

        api_key = self.gemini_api_keys[0]  # Use first key for now

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.gemini_url,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": api_key
                    },
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 600,
                            "topP": 0.9,
                            "topK": 40
                        }
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    raise Exception(f"API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"AI model call failed: {e}")
            raise

    def _extract_best_content_option(self, content: str) -> str:
        """Extract the best single content option when AI provides multiple choices.
        Conservative approach - only parse when we're absolutely sure there are options."""
        import re

        content_stripped = content.strip()

        # Only apply option extraction if we're confident there are multiple options
        option_indicators = [
            'Option 1:', 'Option 2:', 'Option A:', 'Option B:',
            'Here are some options:', 'Here are a few options:',
            'Choose one:', 'Select one:', 'Pick one:'
        ]

        has_options = any(indicator.lower() in content_stripped.lower() for indicator in option_indicators)

        if not has_options:
            # No clear options, return as-is
            return content_stripped

        # Look for clearly marked options
        # Pattern 1: Numbered options (Option 1:, Option 2:, etc.)
        option_pattern = r'Option \d+[:\.\-]\s*([^\n]+)'
        matches = re.findall(option_pattern, content, re.IGNORECASE | re.MULTILINE)
        if matches and len(matches) >= 2:
            # Get the best option (longest and most complete)
            best_option = max(matches, key=lambda x: len(x.strip()))
            if len(best_option.strip()) > 30:  # Reasonable length
                return best_option.strip()

        # Pattern 2: Bulleted list options
        bullet_pattern = r'^\s*[-*•]\s+([^\n]+)'
        lines = content.split('\n')
        bullet_options = []

        for i, line in enumerate(lines):
            if re.match(bullet_pattern, line):
                bullet_options.append(re.sub(bullet_pattern, r'\1', line).strip())
            elif bullet_options and line.strip() == '':
                # Empty line ends the bullet list
                break

        if len(bullet_options) >= 2:
            best_option = max(bullet_options, key=len)
            if len(best_option) > 30:
                return best_option

        # Pattern 3: Quoted options (only if multiple quotes exist)
        quote_pattern = r'"([^"]{30,})"'
        quotes = re.findall(quote_pattern, content)
        if len(quotes) >= 2:
            # Return the most substantial quote
            best_quote = max(quotes, key=len)
            return best_quote.strip()

        # If we can't clearly identify options, return the original content
        # This prevents false positives that truncate good content
        return content_stripped

    def _post_process_content(self, content: str) -> str:
        """Clean and process generated content"""
        import re

        # First, extract the best single option if multiple are provided
        content = self._extract_best_content_option(content)

        # Conservative meta-commentary removal - only clear patterns that are definitely AI chatter
        # These patterns must be at the start of content or be clearly separate thoughts
        meta_patterns = [
            r"^(Okay, I need to.*?)(?=\n\n|$)",
            r"^(Let me.*?)(?=\n\n|$)",
            r"^(Here's what.*?)(?=\n\n|$)",
            r"^(My response.*?)(?=\n\n|$)",
            r"^(I would.*?)(?=\n\n|$)",
            r"^(I think.*?)(?=\n\n|$)",
            r"^(Here are a few options.*?)(?=\n\n|$)",
            r"^(I'm going to.*?)(?=\n\n|$)",
            r"^(The following.*?)(?=\n\n|$)"
        ]

        # Remove meta-commentary only if it appears to be separate from the actual content
        for pattern in meta_patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE | re.MULTILINE)

        # Clean up any remaining AI instruction patterns
        ai_instruction_patterns = [
            r"Write.*?as.*?\.?\n",
            r"Generate.*?for.*?\.?\n",
            r"Create.*?post.*?\.?\n",
            r"Post.*?this.*?as.*?\.?\n"
        ]

        for pattern in ai_instruction_patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE | re.DOTALL)

        # Clean up whitespace
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = content.strip()

        # Remove hashtags and emojis for personal profiles
        content = re.sub(r"#\w+", "", content)
        content = re.sub(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]", "", content)

        return content.strip()

    def _assess_quality(self, content: str, persona_data: Dict[str, Any], platform: str) -> float:
        """Assess content quality"""
        issues = []
        score = 100

        # Length checks
        if len(content) < 20:
            issues.append("Too short")
            score -= 30
        elif len(content) > 2000:
            issues.append("Too long")
            score -= 10

        # Platform-specific checks
        if platform == 'twitter' and len(content) > 280:
            issues.append("Too long for Twitter")
            score -= 20

        # Quality issues
        if not content.strip():
            issues.append("Empty content")
            score = 0

        return max(0, score / 100)  # Return 0-1 scale

    def _assess_quality_with_rag(self, content: str, persona_data: Dict[str, Any],
                                platform: str, rag_examples: List[str]) -> Dict[str, float]:
        """Enhanced quality assessment with RAG metrics and personality consistency"""
        base_score = self._assess_quality(content, persona_data, platform)

        # RAG-specific quality factors
        rag_score = 0
        topic_relevance = 0
        voice_consistency = 0
        personality_consistency = 0

        try:
            # Topic relevance: Check if content is relevant to the retrieved examples
            if rag_examples:
                content_embedding = self.vector_db._create_embedding(content)
                if content_embedding is not None:
                    # Calculate similarity with RAG examples
                    similarities = []
                    for example in rag_examples:
                        example_embedding = self.vector_db._create_embedding(example)
                        if example_embedding is not None:
                            similarity = np.dot(content_embedding, example_embedding) / (
                                np.linalg.norm(content_embedding) * np.linalg.norm(example_embedding)
                            )
                            similarities.append(similarity)

                    if similarities:
                        topic_relevance = np.mean(similarities)
                        logger.debug(f"RAG topic relevance: {topic_relevance:.3f}")

            # Voice consistency: Check how well content matches persona patterns
            if persona_data.get('patterns'):
                voice_patterns = persona_data['patterns']

                # Sentence length consistency
                content_sentences = [s.strip() for s in content.split('.') if s.strip()]
                if content_sentences:
                    avg_length = np.mean([len(s) for s in content_sentences])
                    target_length = voice_patterns.get('sentence_structure', {}).get('avg_sentence_length', 50)
                    length_consistency = max(0, 1 - abs(avg_length - target_length) / target_length)
                else:
                    length_consistency = 0

                # Vocabulary consistency
                content_lower = content.lower()
                target_vocab = voice_patterns.get('vocabulary_profile', {})

                tech_density = target_vocab.get('technical_density', 0)
                casual_density = target_vocab.get('casual_density', 0)

                # Check content vocabulary density
                tech_words = ['api', 'algorithm', 'code', 'tool', 'system', 'tech', 'software', 'platform', 'data']
                casual_words = ['awesome', 'cool', 'shit', 'fuck', 'hell', 'damn', 'wicked', 'sick']

                tech_in_content = sum(1 for word in tech_words if word in content_lower)
                casual_in_content = sum(1 for word in casual_words if word in content_lower)
                total_words = len(content_lower.split())

                if total_words > 0:
                    content_tech_density = tech_in_content / total_words
                    content_casual_density = casual_in_content / total_words

                    vocab_consistency = max(0, 1 - abs(content_tech_density - tech_density))
                    vocab_consistency = vocab_consistency * 0.7  # Weight it
                else:
                    vocab_consistency = 0

                voice_consistency = (length_consistency * 0.6 + vocab_consistency * 0.4)

            # Personality consistency: Check if content matches detected personality characteristics
            detected_personality = getattr(self, '_current_personality_type', 'custom')
            logger.debug(f"Detected personality for consistency check: {detected_personality}")
            personality_consistency = self._assess_personality_consistency(content, detected_personality, platform)

            # Combine RAG-specific scores with enhanced personality weighting
            rag_score = (
                topic_relevance * 0.3 +           # Relevance to examples
                voice_consistency * 0.3 +          # Voice pattern matching
                personality_consistency * 0.3 +    # Personality type alignment
                base_score * 0.1                   # Basic quality
            )

        except Exception as e:
            logger.warning(f"RAG quality assessment failed: {e}")
            rag_score = base_score
            personality_consistency = base_score

        return {
            'voice_consistency': voice_consistency,
            'personality_consistency': personality_consistency,
            'authenticity_prediction': persona_data.get('quality_metrics', {}).get('authenticity_prediction', base_score),
            'engagement_potential': persona_data.get('quality_metrics', {}).get('engagement_potential', base_score),
            'topic_relevance': topic_relevance,
            'overall_quality': max(0, min(1.0, rag_score))
        }

    def _assess_personality_consistency(self, content: str, personality_type: str, platform: str) -> float:
        """Assess how well content matches the actual persona examples dynamically"""
        content_lower = content.lower()

        # Get the current persona data dynamically (don't hardcode!)
        current_persona_data = getattr(self, '_current_persona_data', {})
        persona_examples = current_persona_data.get('examples', [])
        persona_patterns = current_persona_data.get('patterns', {})

        logger.debug(f"Assessing personality consistency for {personality_type} using {len(persona_examples)} examples")

        if not persona_examples:
            logger.debug("No persona examples available for consistency check")
            return 0.5  # Neutral score if no examples

        consistency_score = 0
        total_checks = 0

        # 1. Vocabulary similarity: Compare content vocabulary with persona examples
        try:
            content_words = set(content_lower.split())
            example_words = set()
            for example in persona_examples:
                example_words.update(example.lower().split())

            if content_words and example_words:
                # Calculate vocabulary overlap
                common_words = content_words.intersection(example_words)
                vocab_similarity = len(common_words) / len(content_words.union(example_words))
                consistency_score += vocab_similarity * 0.4
                total_checks += 0.4
                logger.debug(f"Vocabulary similarity: {vocab_similarity:.3f}")

        except Exception as e:
            logger.warning(f"Vocabulary analysis failed: {e}")

        # 2. Style consistency: Analyze writing patterns from examples
        try:
            # Extract style patterns from persona examples
            example_phrases = []
            for example in persona_examples:
                words = example.lower().split()
                # Extract 2-3 word phrases
                for i in range(len(words) - 1):
                    example_phrases.append(' '.join(words[i:i+2]))

            # Check if content uses similar phrases
            content_words = content_lower.split()
            content_phrases = []
            for i in range(len(content_words) - 1):
                content_phrases.append(' '.join(content_words[i:i+2]))

            if example_phrases and content_phrases:
                phrase_matches = len(set(content_phrases).intersection(set(example_phrases)))
                phrase_similarity = phrase_matches / len(set(content_phrases))
                consistency_score += phrase_similarity * 0.3
                total_checks += 0.3
                logger.debug(f"Phrase similarity: {phrase_similarity:.3f}")

        except Exception as e:
            logger.warning(f"Style analysis failed: {e}")

        # 3. Sentence structure consistency
        try:
            # Analyze sentence lengths from examples
            example_sentence_lengths = []
            for example in persona_examples:
                sentences = [s.strip() for s in example.split('.') if s.strip()]
                example_sentence_lengths.extend([len(s) for s in sentences])

            if example_sentence_lengths:
                avg_example_length = sum(example_sentence_lengths) / len(example_sentence_lengths)
                content_sentences = [s.strip() for s in content.split('.') if s.strip()]

                if content_sentences:
                    avg_content_length = sum(len(s) for s in content_sentences) / len(content_sentences)
                    length_consistency = max(0, 1 - abs(avg_content_length - avg_example_length) / max(avg_example_length, 1))
                    consistency_score += length_consistency * 0.2
                    total_checks += 0.2
                    logger.debug(f"Sentence length consistency: {length_consistency:.3f}")

        except Exception as e:
            logger.warning(f"Sentence structure analysis failed: {e}")

        # 4. Platform-appropriate engagement
        engagement_score = self._assess_platform_engagement(content, platform, personality_type)
        consistency_score += engagement_score * 0.1
        total_checks += 0.1

        # Normalize score
        if total_checks > 0:
            consistency_score = consistency_score / total_checks
        else:
            consistency_score = 0.1

        logger.debug(f"Dynamic personality consistency: {consistency_score:.3f} (from {len(persona_examples)} examples)")
        return max(0, min(1.0, consistency_score))

    def _assess_platform_engagement(self, content: str, platform: str, personality_type: str) -> float:
        """Assess if content uses appropriate engagement for the platform and personality"""
        content_lower = content.lower()

        # Platform-specific engagement patterns
        platform_engagement = {
            'twitter': {
                'expected_patterns': ['?', '!', '#'],
                'question_indicators': ['what do you think', 'has anyone', 'who else', 'anyone else'],
                'excitement_indicators': ['mind blown', 'game changer', 'incredible', 'amazing']
            },
            'linkedin': {
                'expected_patterns': ['?', 'professional insights', 'experience shows'],
                'question_indicators': ['what are your thoughts', 'how do you', 'what has been your experience'],
                'professional_indicators': ['strategy', 'approach', 'framework', 'perspective']
            },
            'threads': {
                'expected_patterns': ['!', 'omg', 'wow', 'cool'],
                'casual_indicators': ['okay so', 'just', 'literally', 'you guys'],
                'question_indicators': ['right?', 'what about', 'has anyone else']
            },
            'telegram': {
                'expected_patterns': ['!', '?', 'interesting', 'fascinating'],
                'community_indicators': ['sharing', 'community', 'discussion', 'thoughts'],
                'value_indicators': ['insights', 'analysis', 'breakdown', 'deep dive']
            }
        }

        patterns = platform_engagement.get(platform, {})
        engagement_score = 0
        total_patterns = 0

        # Check for expected patterns
        if 'expected_patterns' in patterns:
            pattern_matches = sum(1 for pattern in patterns['expected_patterns'] if pattern in content)
            engagement_score += min(1.0, pattern_matches / 2)  # At least 2 patterns
            total_patterns += 1

        # Personality-appropriate engagement
        personality_engagement = {
            'tech_founder': {
                'high_energy': ['excited', 'incredible', 'amazing', 'game changer'],
                'business_focus': ['growth', 'scale', 'innovation', 'future']
            },
            'academic_researcher': {
                'analytical': ['analysis', 'research', 'data', 'findings'],
                'thoughtful': ['interesting', 'fascinating', 'noteworthy', 'significant']
            },
            'marketing_influencer': {
                'high_energy': ['amazing', 'incredible', 'awesome', 'literally'],
                'engagement': ['you guys', 'everyone', 'you need to', 'let me know']
            },
            'casual_professional': {
                'balanced': ['interesting', 'thoughtful', 'considering', 'perspective'],
                'engaging': ['what are your thoughts', 'would love to hear', 'curious about']
            }
        }

        persona_patterns = personality_engagement.get(personality_type, {})
        if persona_patterns:
            for pattern_category, keywords in persona_patterns.items():
                matches = sum(1 for keyword in keywords if keyword in content_lower)
                if matches > 0:
                    engagement_score += 0.5
                    total_patterns += 0.5
                    break  # Only count one category

        return engagement_score / total_patterns if total_patterns > 0 else 0.5

    def _calculate_relevance(self, topic: str, example: str) -> float:
        """Calculate relevance score between topic and example"""
        try:
            if not topic or not example:
                return 0.0

            topic_embedding = self.vector_db._create_embedding(topic)
            example_embedding = self.vector_db._create_embedding(example)

            if topic_embedding is not None and example_embedding is not None:
                similarity = np.dot(topic_embedding, example_embedding) / (
                    np.linalg.norm(topic_embedding) * np.linalg.norm(example_embedding)
                )
                return float(similarity)

        except Exception as e:
            logger.warning(f"Relevance calculation failed: {e}")

        return 0.0

    def get_rag_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        try:
            stats = self.vector_db.get_stats()
            return {
                'vector_database': stats,
                'rag_enabled': True,
                'embedding_model': self.voice_analyzer.embedding_model is not None if hasattr(self.voice_analyzer, 'embedding_model') else False
            }
        except Exception as e:
            logger.error(f"Failed to get RAG stats: {e}")
            return {'rag_enabled': False, 'error': str(e)}

    # ========== A/B TESTING METHODS ==========

    def create_ab_test(self, name: str, description: str, test_type: str,
                      persona_id: str, platform: Optional[str] = None,
                      min_sample_size: int = 100, confidence_threshold: float = 0.95) -> str:
        """Create a new A/B test"""
        try:
            type_enum = TestType(test_type)
            return self.ab_testing.create_test(
                name=name,
                description=description,
                test_type=type_enum,
                persona_id=persona_id,
                platform=platform,
                min_sample_size=min_sample_size,
                confidence_threshold=confidence_threshold
            )
        except ValueError as e:
            logger.error(f"Invalid test type: {test_type}")
            raise ValueError(f"Invalid test type: {test_type}. Valid types: {[t.value for t in TestType]}")

    def add_ab_test_variant(self, test_id: str, name: str, description: str,
                           config: Dict[str, Any], variant_type: str = "treatment",
                           traffic_allocation: float = 0.5) -> bool:
        """Add a variant to an A/B test"""
        try:
            type_enum = VariantType(variant_type)
            return self.ab_testing.add_variant(
                test_id=test_id,
                name=name,
                description=description,
                config=config,
                variant_type=type_enum,
                traffic_allocation=traffic_allocation
            )
        except ValueError as e:
            logger.error(f"Invalid variant type: {variant_type}")
            raise ValueError(f"Invalid variant type: {variant_type}. Valid types: {[t.value for t in VariantType]}")

    def start_ab_test(self, test_id: str) -> bool:
        """Start an A/B test"""
        return self.ab_testing.start_test(test_id)

    def complete_ab_test(self, test_id: str, winning_variant_id: Optional[str] = None) -> bool:
        """Complete an A/B test and optionally declare a winner"""
        return self.ab_testing.complete_test(test_id, winning_variant_id)

    def get_ab_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get comprehensive results for an A/B test"""
        return self.ab_testing.get_test_results(test_id)

    def get_active_ab_tests(self) -> List[Dict[str, Any]]:
        """Get all active A/B tests for frontend display"""
        return self.ab_testing.get_active_tests()

    async def generate_content_with_ab_test(self, persona_data: Dict[str, Any], content: Dict[str, Any],
                                          platform: str, user_id: Optional[str] = None,
                                          test_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate content with A/B testing integration"""

        # Get A/B test variant if test_id provided
        variant_config = None
        variant_id = None
        test_info = None

        if test_id:
            variant = self.ab_testing.get_variant_for_request(test_id, user_id)
            if variant:
                variant_config = variant.config
                variant_id = variant.id
                test_info = self.ab_testing.get_test_results(test_id)
                logger.info(f"Using A/B test variant: {variant.name} for test {test_id}")

        # Generate content normally
        result = await self.generate_content(persona_data, content, platform)

        # If A/B test was used, record the metrics
        if test_id and variant_id and result.get('success'):
            quality_score = result.get('quality_score', 0)
            voice_consistency = result.get('voice_consistency', 0)
            personality_consistency = result.get('personality_consistency', 0)
            engagement_score = result.get('engagement_potential', 0)

            self.ab_testing.record_conversion(
                test_id=test_id,
                variant_id=variant_id,
                quality_score=quality_score,
                voice_consistency=voice_consistency,
                personality_consistency=personality_consistency,
                engagement_score=engagement_score
            )

            # Add A/B test info to result
            result['ab_test'] = {
                'test_id': test_id,
                'variant_id': variant_id,
                'variant_name': variant.name,
                'test_info': test_info
            }

        return result

    def create_predefined_tests(self, persona_id: str, platform: Optional[str] = None) -> List[str]:
        """Create predefined A/B tests for common optimization scenarios"""
        created_tests = []

        # Test 1: Prompt Strategy A/B Test
        test1_id = self.create_ab_test(
            name="Prompt Strategy Optimization",
            description="Test different prompt strategies for better content quality",
            test_type="prompt_strategy",
            persona_id=persona_id,
            platform=platform,
            min_sample_size=50
        )

        # Control: Current prompt strategy
        self.add_ab_test_variant(
            test_id=test1_id,
            name="Current Strategy",
            description="Existing prompt generation approach",
            config={"strategy": "current"},
            variant_type="control",
            traffic_allocation=0.5
        )

        # Treatment: Enhanced personality-focused prompts
        self.add_ab_test_variant(
            test_id=test1_id,
            name="Enhanced Personality Focus",
            description="Prompts with stronger personality emphasis",
            config={"strategy": "enhanced_personality"},
            variant_type="treatment",
            traffic_allocation=0.5
        )

        created_tests.append(test1_id)

        # Test 2: Temperature Testing
        test2_id = self.create_ab_test(
            name="AI Temperature Optimization",
            description="Test different AI temperature settings for creativity vs consistency",
            test_type="temperature_testing",
            persona_id=persona_id,
            platform=platform,
            min_sample_size=30
        )

        # Control: Standard temperature (0.8)
        self.add_ab_test_variant(
            test_id=test2_id,
            name="Standard Temperature",
            description="Current temperature setting",
            config={"temperature": 0.8},
            variant_type="control",
            traffic_allocation=0.5
        )

        # Treatment: Lower temperature for consistency
        self.add_ab_test_variant(
            test_id=test2_id,
            name="Consistent Temperature",
            description="Lower temperature for more consistent output",
            config={"temperature": 0.6},
            variant_type="treatment",
            traffic_allocation=0.5
        )

        created_tests.append(test2_id)

        # Test 3: Engagement Hooks Optimization
        test3_id = self.create_ab_test(
            name="Engagement Hooks Optimization",
            description="Test different engagement hook strategies",
            test_type="engagement_hooks",
            persona_id=persona_id,
            platform=platform,
            min_sample_size=40
        )

        # Control: Current engagement approach
        self.add_ab_test_variant(
            test_id=test3_id,
            name="Current Hooks",
            description="Existing engagement hook strategy",
            config={"hooks": "current"},
            variant_type="control",
            traffic_allocation=0.5
        )

        # Treatment: Question-focused engagement
        self.add_ab_test_variant(
            test_id=test3_id,
            name="Question-Focused",
            description="Emphasis on questions and direct engagement",
            config={"hooks": "question_focused"},
            variant_type="treatment",
            traffic_allocation=0.5
        )

        created_tests.append(test3_id)

        logger.info(f"Created {len(created_tests)} predefined A/B tests for persona {persona_id}")
        return created_tests

    def get_ab_test_recommendations(self, persona_id: str) -> Dict[str, Any]:
        """Get A/B test recommendations based on persona performance"""
        # Analyze recent test results and suggest optimizations
        active_tests = self.get_active_ab_tests()
        persona_tests = [test for test in active_tests if test.get('test', {}).get('persona_id') == persona_id]

        recommendations = {
            'current_tests': len(persona_tests),
            'suggested_tests': [],
            'optimization_opportunities': []
        }

        # Suggest tests based on common optimization areas
        if len(persona_tests) == 0:
            recommendations['suggested_tests'] = [
                {
                    'name': 'Initial Prompt Strategy Test',
                    'type': 'prompt_strategy',
                    'description': 'Test basic prompt optimization for this persona',
                    'priority': 'high'
                },
                {
                    'name': 'Platform Optimization',
                    'type': 'platform_optimization',
                    'description': 'Optimize content for specific platforms',
                    'priority': 'medium'
                }
            ]

        # Analyze performance patterns from existing tests
        for test in persona_tests:
            variants = test.get('variants', [])
            if len(variants) >= 2:
                # Check if there are significant performance differences
                scores = [v.get('metrics', {}).get('avg_quality', 0) for v in variants]
                if max(scores) - min(scores) > 0.1:  # Significant difference
                    recommendations['optimization_opportunities'].append({
                        'test_name': test.get('test', {}).get('name'),
                        'opportunity': 'Significant quality variation detected - consider optimizing winning approach',
                        'impact': 'high'
                    })

        return recommendations


# Test function for development
async def test_dynamic_rewriter():
    """Test the dynamic rewriter system"""
    rewriter = DynamicRewriter()

    # Test persona creation
    test_examples = [
        "Just tested DeepSeek R1 from China - surprisingly good for open source. OpenAI should be worried.",
        "Каждый день что-то новое fr fr. Протестировал новый AI тулл для кода - офигенно упрощает жизнь.",
        "По опыту: лучше решить одну реальную проблему клиента, чем нафигачить 20 фич которыми никто не пользуется."
    ]

    persona_info = {
        'name': 'Test Tech Analyst',
        'handle': '@techtest',
        'description': 'Tech analyst who tests AI tools and shares honest opinions',
        'platforms': ['twitter']
    }

    # Create persona
    persona_data = rewriter.create_persona_from_examples(test_examples, persona_info)
    print(f"✅ Persona created: {persona_data['name']}")
    print(f"Quality metrics: {persona_data['quality_metrics']}")

    # Test content generation
    content_data = {
        'topic': 'New AI startup raised $50M for autonomous coding agent',
        'category': 'tech_analysis'
    }

    result = await rewriter.generate_content(persona_data, content_data, 'twitter')
    print(f"\n✅ Generated content:")
    print(f"Quality score: {result.get('quality_score', 0):.2f}")
    print(f"Content: {result.get('content', 'No content generated')}")

    if result.get('success'):
        print(f"\nPrompt used: {result.get('prompt_used', 'No prompt')[:200]}...")


if __name__ == "__main__":
    asyncio.run(test_dynamic_rewriter())