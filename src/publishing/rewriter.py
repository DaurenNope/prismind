#!/usr/bin/env python3
"""
Content Rewriter for Multi-Persona Publishing
Transforms discovered content into platform-optimized posts for different personas
"""

import httpx
import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.publishing.fact_validator import FactValidator
from src.publishing.thread_splitter import ThreadSplitter
from src.publishing.engagement_learner import EngagementLearner
from src.publishing.voice_validator import VoiceValidator
from src.publishing.circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)


class ContentRewriter:
    """
    Rewrites content for different personas and platforms
    
    Personas:
    - Technical Expert: Deep technical insights
    - Startup Builder: Practical applications
    - Learner/Educator: Teaching angle
    - Trendsetter: What's hot and why
    - Thought Leader: Big picture thinking
    
    Platforms:
    - Twitter/X: Short, punchy threads
    - LinkedIn: Professional insights
    - Blog: Long-form deep dives
    - Newsletter: Curated summaries
    """
    
    def __init__(self):
        self.personas = self._load_personas()
        self.ollama_url = "http://localhost:11434/api/generate"

        # Cloud API setup with rotation and fallback support
        # Using Gemini 2.0 Flash Experimental (works reliably with Russian)
        # With 4 keys: 4 × 150 RPD ≈ 600 RPD total (enough for batches)
        self.gemini_model = "gemini-2.0-flash-exp"
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        self.gemini_api_keys = self._load_gemini_keys()
        self.current_key_index = 0
        logger.info(f"✅ Loaded {len(self.gemini_api_keys)} Gemini API key(s) for rotation")

        # Mistral API setup (fallback option with rotation support)
        self.mistral_api_keys = self._load_mistral_keys()
        self.current_mistral_index = 0
        self.mistral_model = "mistral-large-latest"
        self.mistral_url = "https://api.mistral.ai/v1/chat/completions"
        if self.mistral_api_keys:
            logger.info(f"✅ Loaded {len(self.mistral_api_keys)} Mistral API key(s) for rotation")

        # Ollama setup (last resort fallback)
        self.ollama_available = True  # We'll detect on first use

        # Load voice patterns and opinions
        self.voice_patterns = self._load_voice_patterns()
        self.opinions = self._load_opinions()

        # Load voice examples for each persona
        self.voice_examples = self._load_voice_examples()

        # Load rewrite rules (NO HARD-CODED PROMPTS)
        self.rewrite_rules = self._load_rewrite_rules()

        # Analytics tracking
        try:
            from src.publishing.rewrite_analytics import get_analytics
            self.analytics = get_analytics()
        except Exception as e:
            logger.warning(f"Analytics not available: {e}")
            self.analytics = None

        # Fact validator
        self.fact_validator = FactValidator()

        # Thread splitter
        self.thread_splitter = ThreadSplitter(max_length=280)

        # Engagement learner for performance-based example selection
        try:
            self.engagement_learner = EngagementLearner()
            logger.info("✅ Engagement learner initialized")
        except Exception as e:
            logger.warning(f"⚠️ Engagement learner not available: {e}")
            self.engagement_learner = None

        # Voice consistency validator
        try:
            self.voice_validator = VoiceValidator()
            logger.info("✅ Voice validator initialized")
        except Exception as e:
            logger.warning(f"⚠️ Voice validator not available: {e}")
            self.voice_validator = None
        
        # Circuit breaker for API rate limits
        self.circuit_breaker = get_circuit_breaker()
        logger.info("✅ Circuit breaker initialized")
    
    def _load_gemini_keys(self) -> List[str]:
        """Load Gemini API keys from environment for rotation"""
        keys = []

        # Try GEMINI_API_KEY first (single key)
        primary_key = os.getenv("GEMINI_API_KEY")
        if primary_key:
            keys.append(primary_key)

        # Try GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc. (multiple keys)
        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if not key:
                break
            keys.append(key)
            i += 1

        if not keys:
            logger.warning("No Gemini API keys found in environment")

        return keys

    def _load_mistral_keys(self) -> List[str]:
        """Load Mistral API keys from environment for rotation"""
        keys = []

        # Try MISTRAL_API_KEY first (single key)
        primary_key = os.getenv("MISTRAL_API_KEY")
        if primary_key:
            keys.append(primary_key)

        # Try MISTRAL_API_KEY_1, MISTRAL_API_KEY_2, etc. (multiple keys)
        i = 1
        while True:
            key = os.getenv(f"MISTRAL_API_KEY_{i}")
            if not key:
                break
            keys.append(key)
            i += 1

        return keys

    def _get_next_gemini_key(self) -> str:
        """Get next Gemini API key in rotation"""
        if not self.gemini_api_keys:
            return None

        key = self.gemini_api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.gemini_api_keys)
        return key

    def _load_personas(self) -> Dict[str, Dict[str, Any]]:
        """Load persona templates - ONLY 3 PROFILES NOW"""

        return {
            "qronoya": {
                "name": "Qronoya",
                "tone": "professional, approachable, practical",
                "audience": "tech professionals, entrepreneurs, career seekers",
                "style": "Basic but smart - practical tech advice and career insights",
                "emoji": "💡",
                "language": "russian",
                "platforms": ["twitter", "threads", "telegram"]
            },
            "aspandead": {
                "name": "Aspandead",
                "tone": "raw, vulnerable, literary",
                "audience": "humans seeking connection and truth",
                "style": "Deep writer - emotional depth, metaphors, unfiltered observations",
                "emoji": "🖤",
                "language": "russian",
                "platforms": ["twitter", "threads", "telegram", "medium"]
            },
            "claimzilla": {
                "name": "Claimzilla",
                "tone": "engaging, helpful, technical",
                "audience": "crypto anons, defi degens, airdrop hunters",
                "style": "Crypto reply guy - alpha drops, market insights, technical breakdowns",
                "emoji": "💎",
                "language": "english",
                "platforms": ["twitter", "threads"]
            }
        }

    def _load_voice_patterns(self) -> Dict[str, Any]:
        """Load voice patterns from config"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "voice_patterns.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('personas', {})
            logger.warning(f"Voice patterns not found at {config_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading voice patterns: {e}")
            return {}

    def _load_opinions(self) -> Dict[str, Any]:
        """Load opinions from config"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "opinions.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('personas', {})
            logger.warning(f"Opinions not found at {config_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading opinions: {e}")
            return {}

    def _load_voice_examples(self) -> Dict[str, List[str]]:
        """Load voice examples for each persona - FILTER for professional content"""
        examples = {}
        config_dir = Path(__file__).parent.parent.parent / "config" / "personas"

        # Casual words to filter OUT for professional accounts
        casual_markers = ['альтушки', 'скуфы', 'нормисы', 'бамбардилло', 'fr fr', 'was supposed to be', 'Тредс превратился']

        for persona in ["qronoya", "aspandead", "claimzilla"]:
            examples_file = config_dir / f"{persona}_examples.json"
            if examples_file.exists():
                try:
                    with open(examples_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                        # For qronoya: FILTER casual posts, keep only professional
                        if persona == "qronoya":
                            example_texts = []
                            for ex in data.get('examples', []):
                                content = ex.get('content', '').strip()
                                if not content:
                                    continue
                                # Skip if contains casual markers
                                if any(marker.lower() in content.lower() for marker in casual_markers):
                                    continue
                                # Skip very short posts (likely casual)
                                if len(content) < 100:
                                    continue
                                # KEEP THE FULL DICT so we have content_type and structure fields
                                example_texts.append(ex)
                        else:
                            # Other personas: load all examples as dicts
                            example_texts = [
                                ex for ex in data.get('examples', [])
                                if ex.get('content', '').strip()
                            ]

                        examples[persona] = example_texts
                        logger.info(f"Loaded {len(example_texts)} voice examples for {persona}")
                except Exception as e:
                    logger.error(f"Error loading {persona} examples: {e}")
                    examples[persona] = []
            else:
                logger.warning(f"No voice examples found for {persona}")
                examples[persona] = []

        return examples

    def _load_rewrite_rules(self) -> Dict[str, Any]:
        """Load rewrite rules from config (NO HARD-CODED PROMPTS)"""
        try:
            config_dir = Path(__file__).parent.parent.parent / "config"
            rules_file = config_dir / "rewrite_rules.json"

            if rules_file.exists():
                with open(rules_file, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                    logger.info("✅ Loaded rewrite rules from config")
                    return rules
            else:
                logger.warning(f"Rewrite rules not found at {rules_file}")
                return {}
        except Exception as e:
            logger.error(f"Error loading rewrite rules: {e}")
            return {}

    async def rewrite_for_persona(
        self, 
        content: Dict[str, Any], 
        persona: str,
        platform: str = "twitter"
    ) -> Dict[str, Any]:
        """
        Rewrite content for specific persona and platform
        
        Args:
            content: Original content with analysis (from agents)
            persona: Persona ID (technical, builder, learner, etc.)
            platform: Target platform (twitter, linkedin, blog)
            
        Returns:
            Rewritten content optimized for persona and platform
        """
        
        if persona not in self.personas:
            return {"error": f"Unknown persona: {persona}"}
        
        persona_info = self.personas[persona]
        
        logger.info(f"✍️  Rewriting as {persona_info['name']} for {platform}")
        
        # Extract content info
        content_type = content.get("type", "article")
        
        if content_type == "github":
            return await self._rewrite_github(content, persona, platform, persona_info)
        elif content_type == "book":
            return await self._rewrite_book(content, persona, platform, persona_info)
        else:
            return await self._rewrite_article(content, persona, platform, persona_info)
    
    async def _rewrite_github(
        self, 
        content: Dict[str, Any], 
        persona: str,
        platform: str,
        persona_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rewrite GitHub repo content"""
        
        # Get rewrite angle for this persona
        angles = content.get("rewrite_angles", [])
        persona_angle = next((a for a in angles if a["persona"] == persona), angles[0] if angles else {})
        
        # Build prompt
        prompt = f"""Rewrite this GitHub repository as a {persona_info['name']} for {platform}.

Repository: {content.get('name', '')}
Description: {content.get('description', '')}
Stars: {content.get('stars', 0):,}
TLDR: {content.get('tldr', '')}
Use Cases: {', '.join(content.get('use_cases', []))}
Key Features: {', '.join(content.get('key_features', []))}
Why Matters: {content.get('why_matters', '')}
Target Audience: {', '.join(content.get('target_audience', []))}

Angle: {persona_angle.get('angle', '')}
Hook: {persona_angle.get('hook', '')}

Write for:
- Tone: {persona_info['tone']}
- Audience: {persona_info['audience']}
- Style: {persona_info['style']}

Platform constraints:
{"- Thread format, 5-7 tweets, <280 chars each" if platform == "twitter" else ""}
{"- Professional tone, 150-200 words, actionable insights" if platform == "linkedin" else ""}

Rewritten post:"""

        result = await self._call_llm(prompt)
        
        return {
            "persona": persona,
            "persona_emoji": persona_info["emoji"],
            "platform": platform,
            "original_url": content.get("repo_url", ""),
            "rewritten_content": result,
            "angle_used": persona_angle.get("angle", ""),
            "hook": persona_angle.get("hook", ""),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _rewrite_book(
        self,
        content: Dict[str, Any],
        persona: str,
        platform: str,
        persona_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rewrite book content"""
        
        # Get rewrite angle for this persona
        angles = content.get("rewrite_angles", [])
        persona_angle = next((a for a in angles if a["persona"] == persona), angles[0] if angles else {})
        
        prompt = f"""Rewrite this book insight as a {persona_info['name']} for {platform}.

Book: {content.get('title', '')} by {content.get('author', '')}
TLDR: {content.get('tldr', '')}
Key Concepts: {', '.join(content.get('key_concepts', [])[:5])}
Main Arguments: {', '.join(content.get('main_arguments', [])[:3])}
Applications: {', '.join(content.get('practical_applications', [])[:3])}

Angle: {persona_angle.get('angle', '')}
Hook: {persona_angle.get('hook', '')}

Write for:
- Tone: {persona_info['tone']}
- Audience: {persona_info['audience']}
- Style: {persona_info['style']}

Platform constraints:
{"- Thread format, 5-7 tweets, <280 chars each" if platform == "twitter" else ""}
{"- Professional tone, 150-200 words, actionable insights" if platform == "linkedin" else ""}

Rewritten post:"""

        result = await self._call_llm(prompt)
        
        return {
            "persona": persona,
            "persona_emoji": persona_info["emoji"],
            "platform": platform,
            "book_title": content.get("title", ""),
            "rewritten_content": result,
            "angle_used": persona_angle.get("angle", ""),
            "hook": persona_angle.get("hook", ""),
            "timestamp": datetime.now().isoformat()
        }

    def _build_rewrite_instructions(self, persona: str) -> str:
        """Build rewrite instructions dynamically from config (NO HARD-CODING)"""
        if not self.rewrite_rules:
            logger.warning("No rewrite rules loaded, using minimal instructions")
            return "Extract core ideas and rewrite in persona's authentic voice."

        global_rules = self.rewrite_rules.get('global_rules', {})
        persona_instructions = self.rewrite_rules.get('persona_specific_instructions', {}).get(persona, {})

        # Build instruction text
        instructions = []

        # Global rules - personal profile enforcement
        personal_profile = global_rules.get('personal_profile_enforcement', {})

        if personal_profile:
            instructions.append("🚨 CRITICAL - PERSONAL PROFILE RULES (ABSOLUTELY MANDATORY):")
            instructions.append("")

            # Emojis
            emoji_rules = personal_profile.get('emojis', {})
            if emoji_rules:
                instructions.append(f"1. {emoji_rules.get('usage', 'NEVER')} EMOJIS - {emoji_rules.get('reason', '')}")
                instructions.append(f"   ❌ DO NOT USE: {', '.join(emoji_rules.get('examples_to_avoid', []))}")
                instructions.append(f"   ✅ {emoji_rules.get('guidance', '')}")
                instructions.append("")

            # Hashtags
            hashtag_rules = personal_profile.get('hashtags', {})
            if hashtag_rules:
                instructions.append(f"2. {hashtag_rules.get('usage', 'NEVER')} HASHTAGS - {hashtag_rules.get('reason', '')}")
                instructions.append(f"   ❌ DO NOT USE: {', '.join(hashtag_rules.get('examples_to_avoid', []))}")
                instructions.append(f"   ✅ {hashtag_rules.get('guidance', '')}")
                instructions.append("")

            # Corporate language
            corporate_rules = personal_profile.get('corporate_language', {})
            if corporate_rules:
                instructions.append(f"3. {corporate_rules.get('usage', 'NEVER')} CORPORATE LANGUAGE - {corporate_rules.get('reason', '')}")
                instructions.append(f"   ❌ Avoid: {', '.join(corporate_rules.get('phrases_to_avoid', []))}")
                instructions.append(f"   ✅ {corporate_rules.get('guidance', '')}")
                instructions.append("")

        # Rewriting approach
        rewriting_approach = global_rules.get('rewriting_approach', {})
        if rewriting_approach:
            instructions.append("REWRITING APPROACH:")
            for idx, (key, value) in enumerate(rewriting_approach.items(), 4):
                instructions.append(f"{idx}. {value}")
            instructions.append("")

        # Persona-specific instructions
        if persona_instructions:
            primary_instruction = persona_instructions.get('primary_instruction', '')
            if primary_instruction:
                instructions.append(f"PERSONA-SPECIFIC ({persona.upper()}):")
                instructions.append(primary_instruction)
                instructions.append("")

        return '\n'.join(instructions)

    async def _rewrite_article(
        self,
        content: Dict[str, Any],
        persona: str,
        platform: str,
        persona_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rewrite article/blog content"""

        prompt = f"""Rewrite this article as a {persona_info['name']} for {platform}.

Title: {content.get('title', '')}
Summary: {content.get('content_summary', content.get('content', '')[:300])}

Write for:
- Tone: {persona_info['tone']}
- Audience: {persona_info['audience']}
- Style: {persona_info['style']}

Platform constraints:
{"- Thread format, 5-7 tweets, <280 chars each" if platform == "twitter" else ""}
{"- Professional tone, 150-200 words, actionable insights" if platform == "linkedin" else ""}

Rewritten post:"""

        result = await self._call_llm(prompt)

        return {
            "persona": persona,
            "persona_emoji": persona_info["emoji"],
            "platform": platform,
            "original_url": content.get("url", ""),
            "rewritten_content": result,
            "timestamp": datetime.now().isoformat()
        }

    def _classify_content_type(self, content: str, category: str = "", topics: List[str] = None, persona: str = "qronoya") -> str:
        """
        Classify content to determine which type of examples to use.
        Classification depends on the persona.

        Qronoya (tech) types:
        - product_launch, feature_update, funding_news, trend_analysis, research_finding, pricing_update

        Aspandead (relationships) types:
        - dating_story, relationship_insight, healing_journey, intimacy_reflection, breakup_experience, modern_dating

        Returns: content_type string
        """
        content_lower = content.lower()

        # ASPANDEAD: Relationship/emotional content classification
        if persona == "aspandead":
            # Breakup/ending keywords
            if any(kw in content_lower for kw in ['broke', 'breakup', 'ended', 'left', 'ex', 'closure', 'goodbye']):
                return "breakup_experience"

            # Healing/growth keywords
            if any(kw in content_lower for kw in ['healing', 'therapy', 'growth', 'recovering', 'moving on', 'letting go', 'free']):
                return "healing_journey"

            # Modern dating keywords (apps, tech)
            if any(kw in content_lower for kw in ['dating app', 'tinder', 'bumble', 'swipe', 'match', 'profile', 'online dating']):
                return "modern_dating"

            # Intimacy/vulnerability keywords
            if any(kw in content_lower for kw in ['intimacy', 'vulnerable', 'seen', 'walls', 'armor', 'guard', 'open up']):
                return "intimacy_reflection"

            # Dating story keywords (narrative, specific moments)
            if any(kw in content_lower for kw in ['date', 'met', 'coffee', 'talked', 'walked', 'night', 'moment']):
                return "dating_story"

            # Default to relationship insight
            return "relationship_insight"

        # QRONOYA: Tech content classification
        else:
            # Funding/investment keywords
            if any(kw in content_lower for kw in ['привлек', 'раунд', '$', 'инвестиц', 'funding', 'series', 'raised']):
                return "funding_news"

            # Research/study keywords
            if any(kw in content_lower for kw in ['исследование', 'показал', 'точность', '%', 'research', 'study', 'mit']):
                return "research_finding"

            # Pricing keywords
            if any(kw in content_lower for kw in ['цен', 'бесплатн', 'pricing', 'free', 'снизил', 'дороже', 'дешевле']):
                return "pricing_update"

            # Product launch keywords (новый продукт)
            if any(kw in content_lower for kw in ['вышел', 'выпустил', 'запустил', 'released', 'launched', 'announced', 'выкатил']):
                return "product_launch"

            # Feature update keywords (обновление существующего)
            if any(kw in content_lower for kw in ['добавил', 'теперь', 'новая функция', 'added', 'now supports', 'update']):
                return "feature_update"

            # Default to trend analysis for opinion/analysis pieces
            return "trend_analysis"

    def _detect_content_tone(self, content: str) -> str:
        """
        Detect emotional tone of content for better example matching

        Returns: vulnerable, analytical, critical, optimistic, neutral
        """
        content_lower = content.lower()

        # Vulnerable/emotional keywords
        vulnerable_words = ['feel', 'emotion', 'heart', 'pain', 'fear', 'love', 'hurt', 'vulnerable', 'scared', 'anxiety']
        vulnerable_score = sum(1 for word in vulnerable_words if word in content_lower)

        # Analytical/technical keywords
        analytical_words = ['data', 'research', 'study', 'analysis', 'metric', 'performance', 'efficiency', 'algorithm']
        analytical_score = sum(1 for word in analytical_words if word in content_lower)

        # Critical/questioning keywords
        critical_words = ['why', 'problem', 'issue', 'concern', 'wrong', 'fail', 'mistake', 'bad']
        critical_score = sum(1 for word in critical_words if word in content_lower)

        # Optimistic/positive keywords
        optimistic_words = ['great', 'amazing', 'excellent', 'opportunity', 'success', 'best', 'love', 'perfect']
        optimistic_score = sum(1 for word in optimistic_words if word in content_lower)

        # Determine primary tone
        scores = {
            'vulnerable': vulnerable_score,
            'analytical': analytical_score,
            'critical': critical_score,
            'optimistic': optimistic_score
        }

        max_score = max(scores.values())
        if max_score == 0:
            return 'neutral'

        return max(scores, key=scores.get)

    async def _select_smart_examples(
        self,
        examples: List[Any],
        content_type: str,
        content_length: int,
        content_text: str = "",
        persona: Optional[str] = None,
        platform: Optional[str] = None,
        use_performance_weighting: bool = True
    ) -> List[str]:
        """
        Intelligently select examples based on:
        - Performance data (if available) - NEW!
        - Content type (primary)
        - Structure (length-based)
        - Tone (emotional vs analytical)
        - Variety (mix of styles)

        Args:
            examples: List of voice examples (can be strings or dicts)
            content_type: Classified content type
            content_length: Length of original content
            content_text: Original content for tone detection
            persona: Persona key (for performance weighting)
            platform: Platform name (for performance weighting)
            use_performance_weighting: Whether to use engagement learner (default True)

        Returns:
            List of 3-5 selected example strings
        """
        import random

        logger.info(f"📚 Smart selection: {content_type}, {content_length} chars, {len(examples)} total examples")

        # TRY PERFORMANCE-WEIGHTED SELECTION FIRST (if available)
        if use_performance_weighting and self.engagement_learner and persona and platform:
            try:
                logger.info(f"🎯 Using performance-weighted example selection for {persona}/{platform}")

                # Extract example texts
                def get_example_text(ex):
                    if isinstance(ex, dict):
                        return ex.get('content', '')
                    return str(ex)

                example_texts = [get_example_text(ex) for ex in examples if get_example_text(ex)]

                # Get performance-weighted examples
                weighted_examples = await self.engagement_learner.get_weighted_examples(
                    persona=persona,
                    platform=platform,
                    all_examples=example_texts,
                    count=5
                )

                if weighted_examples and len(weighted_examples) >= 3:
                    logger.info(f"✅ Selected {len(weighted_examples)} performance-weighted examples")
                    return weighted_examples
                else:
                    logger.warning(f"⚠️ Performance weighting returned insufficient examples, falling back to smart selection")

            except Exception as e:
                logger.warning(f"⚠️ Performance weighting failed: {e}, falling back to smart selection")

        # FALLBACK TO SMART SELECTION (original algorithm)

        # Handle both string examples and dict examples
        def get_example_text(ex):
            if isinstance(ex, dict):
                return ex.get('content', '')
            return str(ex)

        def get_example_type(ex):
            if isinstance(ex, dict):
                return ex.get('content_type', '')
            return ''

        def get_example_structure(ex):
            if isinstance(ex, dict):
                return ex.get('structure', '')
            return ''

        # Filter professional examples (skip scraped personal posts)
        professional_examples = [
            ex for ex in examples
            if isinstance(ex, dict) and 'content_type' in ex
        ]

        logger.info(f"📚 Found {len(professional_examples)} professional examples with content_type")

        if not professional_examples:
            # Fallback to random if no categorized examples
            logger.warning(f"⚠️ No professional examples found - falling back to random selection")
            num_examples = min(5, len(examples))
            return [get_example_text(ex) for ex in random.sample(examples, num_examples)]

        # Detect content tone for better matching
        content_tone = self._detect_content_tone(content_text) if content_text else 'neutral'
        logger.info(f"🎭 Detected tone: {content_tone}")

        # PRIMARY: Match by content_type (strongest signal)
        type_matches = [ex for ex in professional_examples if get_example_type(ex) == content_type]

        # SECONDARY: Match by structure based on length
        if content_length < 200:
            # Short content: prefer concise, practical examples
            structure_matches = [ex for ex in professional_examples if get_example_structure(ex) in ['concise', 'practical', 'moment_captured']]
        elif content_length > 800:
            # Long content: prefer analytical, detailed examples
            structure_matches = [ex for ex in professional_examples if get_example_structure(ex) in ['data_driven', 'observational', 'problem_solution', 'philosophical']]
        else:
            # Medium content: prefer narrative, questioning styles
            structure_matches = [ex for ex in professional_examples if get_example_structure(ex) in ['narrative', 'questioning', 'revelation']]

        # TERTIARY: Match by tone (vulnerable vs analytical)
        tone_matches = []
        if content_tone == 'vulnerable':
            # Prefer vulnerable, emotional examples
            tone_matches = [ex for ex in professional_examples if get_example_structure(ex) in ['revelation', 'questioning', 'narrative']]
        elif content_tone == 'analytical':
            # Prefer analytical, wisdom-based examples
            tone_matches = [ex for ex in professional_examples if get_example_structure(ex) in ['wisdom', 'philosophical', 'observational']]

        # Build selection pool with weighted priorities
        selected = []

        # 1. Take 2-3 type matches (HIGHEST PRIORITY)
        if type_matches:
            num_type = min(3, len(type_matches))
            selected.extend(random.sample(type_matches, num_type))
            logger.info(f"  ✓ Added {len(selected)} content-type matches ({content_type})")

        # 2. Add 1-2 structure matches (if available and not duplicates)
        remaining_structure = [ex for ex in structure_matches if ex not in selected]
        if remaining_structure and len(selected) < 5:
            num_structure = min(2, len(remaining_structure), 5 - len(selected))
            selected.extend(random.sample(remaining_structure, num_structure))
            logger.info(f"  ✓ Added structure matches, total: {len(selected)}")

        # 3. Add 1 tone match for variety (if available and not duplicate)
        remaining_tone = [ex for ex in tone_matches if ex not in selected]
        if remaining_tone and len(selected) < 5:
            selected.append(random.choice(remaining_tone))
            logger.info(f"  ✓ Added tone match ({content_tone}), total: {len(selected)}")

        # 4. Fill remaining slots with random professional examples for variety
        remaining_professional = [ex for ex in professional_examples if ex not in selected]
        if remaining_professional and len(selected) < 5:
            num_random = min(5 - len(selected), len(remaining_professional))
            selected.extend(random.sample(remaining_professional, num_random))

        # Ensure we have at least 3 examples
        if len(selected) < 3 and professional_examples:
            needed = 3 - len(selected)
            remaining = [ex for ex in professional_examples if ex not in selected]
            if remaining:
                selected.extend(random.sample(remaining, min(needed, len(remaining))))

        logger.info(f"📚 Final selection: {len(selected)} examples (type: {len(type_matches)}, structure: {len(structure_matches)}, tone: {len(tone_matches)})")

        return [get_example_text(ex) for ex in selected]

    def _humanize_text(self, text: str, persona: str) -> str:
        """
        Add human-like touches to make text feel more authentic:
        - Convert em-dashes (—) to single dashes with spaces ( - )
        - Occasionally remove a comma for casual flow (5% chance)
        - Fix double spaces

        Args:
            text: Text to humanize
            persona: Persona name (for future persona-specific humanization)

        Returns:
            Humanized text
        """
        import re
        import random

        # 1. Fix dashes: em-dash (—) → single dash with spaces ( - )
        text = re.sub(r'\s*—\s*', ' - ', text)  # em-dash with any spacing → " - "
        text = re.sub(r'\s*–\s*', ' - ', text)  # en-dash → " - "

        # 2. Occasionally remove a comma for casual grammar (very subtle - 5% per comma)
        # This makes it feel like you're typing fast and missed one
        sentences = text.split('\n')
        humanized_sentences = []

        for sentence in sentences:
            # Find commas that could be "accidentally" skipped
            # Skip if it's the last comma in sentence (would be weird to remove)
            commas = [m.start() for m in re.finditer(',', sentence)]

            if commas and random.random() < 0.05:  # 5% chance per sentence
                # Remove one random comma (not the last one)
                if len(commas) > 1:
                    comma_to_remove = random.choice(commas[:-1])
                    sentence = sentence[:comma_to_remove] + sentence[comma_to_remove+1:]
                    logger.debug(f"🎭 Humanization: Removed comma for casual feel")

            humanized_sentences.append(sentence)

        text = '\n'.join(humanized_sentences)

        # 3. Fix double spaces
        text = re.sub(r'  +', ' ', text)

        # 4. Ensure consistent spacing around punctuation
        text = re.sub(r'\s+([.!?])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([.!?])([А-Яа-яA-Za-z])', r'\1 \2', text)  # Add space after punctuation

        return text

    def _validate_output_length(self, content: str, platform: str, is_thread: bool) -> Dict[str, Any]:
        """
        Validate output fits platform constraints

        Returns dict with:
        - valid: bool
        - warnings: List[str]
        - tweet_count: int (for threads)
        - max_tweet_length: int (for threads)
        """
        warnings = []

        if is_thread:
            # Split by thread markers (1/, 2/, 3/, etc.)
            import re
            tweets = re.split(r'\n\d+/\n', content)
            tweets = [t.strip() for t in tweets if t.strip()]

            max_length = 0
            over_limit = []

            for i, tweet in enumerate(tweets, 1):
                length = len(tweet)
                max_length = max(max_length, length)

                if platform in ['twitter', 'threads'] and length > 280:
                    over_limit.append(f"Tweet {i}: {length} chars (max 280)")
                    warnings.append(f"⚠️ Tweet {i} exceeds 280 characters ({length} chars)")

            return {
                "valid": len(over_limit) == 0,
                "warnings": warnings,
                "tweet_count": len(tweets),
                "max_tweet_length": max_length,
                "over_limit_tweets": over_limit
            }
        else:
            # Single post
            length = len(content)

            if platform == 'twitter' and length > 280:
                warnings.append(f"⚠️ Tweet exceeds 280 characters ({length} chars)")
                return {"valid": False, "warnings": warnings, "length": length}
            elif platform == 'threads' and length > 500:
                warnings.append(f"⚠️ Threads post exceeds 500 characters ({length} chars)")
                return {"valid": False, "warnings": warnings, "length": length}

            return {"valid": True, "warnings": [], "length": length}

    def _score_output_quality(self, rewritten: str, persona: str, examples: List[Any]) -> Dict[str, Any]:
        """
        Score rewritten content quality 0-100

        Checks:
        - No forbidden elements (emojis, hashtags, corporate language)
        - Vocabulary matches examples
        - No repetitive patterns
        - Authentic voice

        Returns dict with score and feedback
        """
        score = 100
        issues = []

        # Check for emojis (should be zero)
        import re
        emoji_pattern = re.compile('['
            u'\U0001F600-\U0001F64F'  # emoticons
            u'\U0001F300-\U0001F5FF'  # symbols & pictographs
            u'\U0001F680-\U0001F6FF'  # transport & map symbols
            u'\U0001F1E0-\U0001F1FF'  # flags
            u'\U00002702-\U000027B0'
            u'\U000024C2-\U0001F251'
            u'\U0001F900-\U0001F9FF'  # supplemental symbols
            u'\U0001FA70-\U0001FAFF'
            ']+', flags=re.UNICODE)

        emoji_matches = emoji_pattern.findall(rewritten)
        if emoji_matches:
            score -= 20
            issues.append(f"Contains {len(emoji_matches)} emoji(s): {emoji_matches[:3]}")

        # Check for hashtags (should be zero)
        hashtag_pattern = re.compile(r'#\w+')
        hashtag_matches = hashtag_pattern.findall(rewritten)
        if hashtag_matches:
            score -= 15
            issues.append(f"Contains {len(hashtag_matches)} hashtag(s): {hashtag_matches[:3]}")

        # Check for corporate language
        corporate_phrases = [
            'join us', 'follow for more', 'don\'t miss out', 'click the link',
            'subscribe now', 'check out our', 'visit our website', 'learn more at'
        ]
        found_corporate = [phrase for phrase in corporate_phrases if phrase in rewritten.lower()]
        if found_corporate:
            score -= 10
            issues.append(f"Corporate language detected: {found_corporate}")

        # Check for repetitive phrases (same phrase appears 3+ times)
        words = rewritten.lower().split()
        from collections import Counter

        # Check 3-word phrases
        trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        trigram_counts = Counter(trigrams)
        repetitive = {phrase: count for phrase, count in trigram_counts.items() if count >= 3}

        if repetitive:
            score -= 10
            issues.append(f"Repetitive phrases: {list(repetitive.keys())[:2]}")

        # Check minimum length (too short might be incomplete)
        if len(rewritten.strip()) < 50:
            score -= 15
            issues.append(f"Content too short: {len(rewritten)} chars")

        return {
            "score": max(0, score),
            "quality": "excellent" if score >= 90 else "good" if score >= 70 else "needs_improvement",
            "issues": issues,
            "passed": score >= 70
        }

    async def rewrite_analyzed_post(
        self,
        analyzed_content: Dict[str, Any],
        persona: str,
        platform: str = "auto",
        generate_variations: int = 1,
        custom_prompt: Optional[str] = None,
        platform_constraints: Optional[Dict[str, Any]] = None,
        target_content_type: Optional[str] = None,
        _retry_attempt: int = 0
    ) -> Dict[str, Any]:
        """
        Rewrite an analyzed social media post using enhanced rewrite_angles.

        This method leverages the improved analyzer output with:
        - rewrite_angles (with tone, CTA, platform_fit)
        - discovery_signals
        - content_freshness

        Args:
            analyzed_content: Full analysis from IntelligentContentAnalyzer
            persona: Persona to use (technical, builder, learner, trendsetter, thought_leader)
            platform: Target platform ("auto" uses platform_fit from angle)
            custom_prompt: Optional pre-built prompt from ProfileContentPipeline (overrides internal prompt generation)
            platform_constraints: Optional platform constraints from profile config (max_length, use_line_breaks, etc.)
            target_content_type: Optional content type for context-aware extraction (tech_news, deep_analysis, etc.)

        Returns:
            Rewritten content optimized for persona and platform
        """

        if persona not in self.personas:
            return {"error": f"Unknown persona: {persona}"}

        # Get the rewrite angle for this persona
        rewrite_angles = analyzed_content.get('rewrite_angles', [])
        persona_angle = next((a for a in rewrite_angles if a['persona'] == persona), None)

        if not persona_angle:
            return {"error": f"No rewrite angle found for persona: {persona}"}

        # Use platform_fit from angle if platform is "auto"
        if platform == "auto":
            platform_fit = persona_angle.get('platform_fit', 'twitter_thread')
            if 'twitter' in platform_fit:
                platform = 'twitter'
            elif 'linkedin' in platform_fit:
                platform = 'linkedin'
            else:
                platform = 'twitter'  # Default

        persona_info = self.personas[persona]

        logger.info(f"✍️  Rewriting {analyzed_content.get('post_id')} as {persona_info['name']} for {platform}")
        logger.info(f"   Using angle: {persona_angle.get('angle')}")

        # Extract original content info
        original_content = analyzed_content.get('summary', analyzed_content.get('content', ''))

        # VALIDATION: Check for truncated/incomplete content
        if not original_content or len(original_content.strip()) == 0:
            logger.warning("⚠️ Content is empty - skipping")
            return {"error": "Content is empty", "skipped": True}

        # Check for truncation indicators (ending with ... means incomplete)
        # NOTE: We allow short content - it might be a concise banger post
        truncation_indicators = ['...', '…', '[truncated]', '[...]']
        if any(indicator in original_content[-20:] for indicator in truncation_indicators):
            logger.warning("⚠️ Content appears truncated (ends with ...) - skipping")
            return {"error": "Content appears truncated - cannot rewrite incomplete content", "skipped": True}

        # Check if content starts with truncation (incomplete beginning)
        if any(indicator in original_content[:20] for indicator in truncation_indicators):
            logger.warning("⚠️ Content appears truncated (starts with ...) - skipping")
            return {"error": "Content appears truncated - cannot rewrite incomplete content", "skipped": True}

        category = analyzed_content.get('category', '')
        topics = analyzed_content.get('topics') or []
        key_concepts = analyzed_content.get('key_concepts') or []

        # Get enhanced angle fields
        angle_tone = persona_angle.get('tone', persona_info['tone'])
        hook = persona_angle.get('hook', '')
        key_points = persona_angle.get('key_points', [])
        call_to_action = persona_angle.get('call_to_action', '')
        target_audience = persona_angle.get('target_audience', persona_info['audience'])

        # Determine format based on platform_fit
        platform_fit = persona_angle.get('platform_fit', 'single_post')
        # Only treat as thread if EXPLICITLY marked as thread (not just contains word "thread")
        is_thread = platform_fit in ['twitter_thread', 'threads_thread', 'thread']

        if is_thread:
            format_constraint = "Thread format: 3-7 tweets, each <280 chars"
            format_instructions = """🚨 CRITICAL THREAD FORMAT RULES:

CORRECT FORMAT (number on own line):
1/
First tweet content goes here. Max 280 characters per tweet.

2/
Second tweet content here.

3/
Third tweet content here.

WRONG FORMAT (DO NOT USE):
❌ "1/ Text here" - Number and text on same line
❌ "Tweet 1: Text" - No numbering style
❌ No line break after number

VALIDATION:
- Each tweet MUST be under 280 characters
- Number MUST be on its own line with "/"
- MUST have blank line before content
- Test: Can you split on "\n\d+/\n" pattern?

IMPORTANT: Only use threads if content needs 3+ tweets. Single post is preferred."""
        elif 'short' in platform_fit:
            format_constraint = "Single tweet: <280 chars, punchy and direct"
            format_instructions = "Write a single, standalone post. NO thread format needed."
        elif 'linkedin' in platform_fit:
            format_constraint = "LinkedIn post: 150-300 words, professional tone"
            format_instructions = "Write a single LinkedIn post. NO thread numbering."
        else:
            format_constraint = "Single post, optimized for engagement"
            format_instructions = "Write a single, standalone post. NO thread format needed."

        # Get voice patterns and opinions for this persona
        voice_pattern = self.voice_patterns.get(persona, {})
        persona_opinions = self.opinions.get(persona, {})
        examples = self.voice_examples.get(persona, [])

        # Extract voice guidance
        vocabulary = voice_pattern.get('vocabulary', {})
        sentence_patterns = voice_pattern.get('sentence_patterns', {})
        tone_markers = voice_pattern.get('tone_markers', {})
        quirks = voice_pattern.get('quirks', [])

        # Build voice examples section (if available)
        voice_examples_text = ""
        if examples:
            # SMART EXAMPLE SELECTION - match examples to content type and characteristics
            content_type = self._classify_content_type(original_content, category, topics, persona=persona)
            content_length = len(original_content)
            logger.info(f"🔍 Classified as: {content_type} ({content_length} chars)")
            examples_sample = await self._select_smart_examples(
                examples,
                content_type,
                content_length,
                original_content,
                persona=persona,
                platform=platform
            )

            voice_examples_text = f"""

EXAMPLES - Study how {persona_info['name']} writes (notice the variety in structure, openings, endings):

{chr(10).join(f'Example {i+1}:{chr(10)}{ex}{chr(10)}' for i, ex in enumerate(examples_sample))}

Notice:
- Each example has DIFFERENT structure
- Different opening styles (direct, questioning, observational, bold statement)
- Different ending styles (insight, question, statement, cliffhanger)
- Natural vocabulary - not forced patterns
- Mix of lengths and complexity
"""

        # Build opinions section (if available)
        opinions_text = ""
        if persona_opinions:
            opinions_text = f"""

PERSONA OPINIONS & STANCES:
{chr(10).join(f"- {topic}: {stance}" for topic, stances in list(persona_opinions.items())[:2] for stance in [stances] if isinstance(stances, str))}
(Use these viewpoints naturally if relevant to the content)
"""

        # Language instruction
        language_instruction = ""
        if persona_info.get('language') == 'russian':
            language_instruction = "\n⚠️  CRITICAL: Write ENTIRELY in RUSSIAN language. This is a Russian-language profile. Do NOT write in English."
        else:
            language_instruction = "\n✓ Write in English language."

        # Determine language for LLM call
        llm_language = "russian" if persona_info.get('language') == 'russian' else "english"

        # TWO-STAGE PIPELINE FOR RUSSIAN: Extract ideas first, then write
        if llm_language == "russian":
            logger.info("🔄 Using TWO-STAGE pipeline: Gemini extraction → Gemini writing")

            # Stage 1: Extract core ideas using Gemini (cloud-based)
            extracted_ideas = await self._extract_core_ideas(
                original_content,
                analyzed_content,
                target_platform=platform,
                target_content_type=target_content_type
            )

            # ERROR HANDLING: Check if extraction failed due to rate limits
            # If Stage 1 returns an error, FAIL immediately instead of passing error text to Stage 2
            from src.utils.error_handler import is_rate_limit_error_in_content, create_rate_limit_error_result

            if is_rate_limit_error_in_content(extracted_ideas):
                logger.error(f"❌ Stage 1 extraction failed with rate limit/error - FAILING output instead of propagating")
                return create_rate_limit_error_result(
                    post_id=analyzed_content.get('post_id', 'unknown'),
                    platform=analyzed_content.get('platform', 'unknown'),
                    persona_name=persona_info.get('name', persona),
                    provider="Gemini",
                    stage="extraction"
                )

            # Stage 2: Write from ideas using Gemini (Russian-native)
            logger.info("✍️  Stage 2: Writing in Russian with Gemini from extracted ideas")

            # Get the angle/strategy from rewrite_angles
            angle_strategy = analyzed_content.get('rewrite_angles', [{}])[0].get('angle', '')

            # Define strategy-specific instructions
            strategy_instructions = ""
            if 'short' in angle_strategy.lower() or 'короткий' in angle_strategy.lower() or 'punchy' in angle_strategy.lower():
                strategy_instructions = """
WRITING STRATEGY: SHORT & PUNCHY
- Maximum 3-4 sentences total
- Add line break (\\n\\n) after EVERY sentence for readability
- Direct, minimal, no fluff
- Each line = complete thought"""

            elif 'expanded' in angle_strategy.lower() or 'развёрнутый' in angle_strategy.lower() or 'context' in angle_strategy.lower():
                strategy_instructions = """
WRITING STRATEGY: EXPANDED WITH CONTEXT
- Add specific details: numbers, comparisons, examples
- Explain WHY this matters or what it means
- Add line breaks (\\n\\n) every 1-2 sentences
- Include background context or concrete data points
- Make it informative and thorough (5-7 sentences)"""

            elif 'provocative' in angle_strategy.lower() or 'story' in angle_strategy.lower() or 'провокационный' in angle_strategy.lower() or 'personal' in angle_strategy.lower():
                strategy_instructions = """
WRITING STRATEGY: PROVOCATIVE/STORY
- Start with controversial statement or personal admission
- Use first-person angle ("я думал X, оказалось Y")
- Add line breaks (\\n\\n) for dramatic pauses
- Create tension, irony, or contradiction
- End with provocative question to audience"""

            else:
                # Default: balanced approach with line breaks
                strategy_instructions = """
WRITING STRATEGY: BALANCED
- Add line breaks (\\n\\n) every 1-2 sentences for Twitter readability
- Keep concise but informative"""

            # Use custom prompt from profile pipeline if provided, otherwise build internal prompt
            if custom_prompt:
                logger.info("📝 Using custom prompt from ProfileContentPipeline")
                prompt = custom_prompt
                # Replace placeholders in custom prompt with actual content
                prompt = prompt.replace('{extracted_ideas}', extracted_ideas)
                prompt = prompt.replace('{voice_examples}', voice_examples_text)
            else:
                logger.info("📝 Building internal prompt")
                prompt = f"""You are {persona_info['name']}, writing for {platform}.

TOPIC:
{extracted_ideas}

{strategy_instructions}

VOICE EXAMPLES - Study these to match your style:
{voice_examples_text}

CORE RULES:
1. Write in RUSSIAN
2. Platform: {platform} ({format_constraint})
3. CRITICAL: Add line breaks (\\n\\n) between sentences for readability
4. If source has an opinion/preference, KEEP that sentiment (don't flip positive to negative)
5. Use ONLY facts from source - don't invent product names or features
6. Match the voice examples' tone and structure
{opinions_text}

Write the post:"""

            result = await self._call_llm(prompt, max_tokens=800, language="russian")

        else:
            # SINGLE-STAGE FOR ENGLISH (use same quality approach as Russian)
            logger.info("📝 Using SINGLE-STAGE pipeline for English")

            prompt = f"""You are {persona_info['name']}, writing for {platform}.

CONTENT IDEAS TO WORK WITH:
- Main topic: {category}
- Key concepts: {', '.join(key_concepts)}
- Context: {original_content}

YOUR TASK:
Write this as a social media post in {persona_info['name']}'s authentic voice. Study the examples below to understand HOW this person writes - the rhythm, variety, natural style. Don't follow formulas or patterns.

{voice_examples_text}

VOICE GUIDELINES:
{chr(10).join(f"- {trait}" for trait in persona_info.get('traits', []))}
{language_instruction}

FORMAT:
{format_instructions}

WRITING STYLE:
- Be CONCISE and PUNCHY - avoid unnecessary elaboration
- Don't add details that weren't in the original content
- Sound like a real person, not an AI trying to be helpful
- Get to the point quickly, then stop
- Use single dash with spaces (like " - ") not em-dash (—)
- Occasional minor imperfections are OK (missing comma, casual grammar) - you're human writing fast

CREATIVITY IS KEY:
- Each post should feel unique and spontaneous
- Vary structure, length, opening, ending every time
- Don't repeat phrases or patterns from post to post
- Write like a real person sharing interesting content, not following a template
{opinions_text}

IMPORTANT:
- NO emojis (🚀💎✨) - personal account, not a brand
- NO hashtags (#crypto #AI) - personal account style
- NO corporate speak ("join us", "don't miss out")
- Just write naturally like YOU

Write the post now (JUST THE POST, no labels like "Hook:" or "Key Points:", just the actual content):"""

            result = await self._call_llm(prompt, max_tokens=800, language="english")

        # 🚨 POST-PROCESSING: Enforce ZERO emojis/hashtags for personal profiles
        # Remove any emojis that slipped through
        import re

        # Remove <think> tags from Vikhr model output
        think_pattern = re.compile(r'<think>.*?</think>', re.DOTALL)
        result = think_pattern.sub('', result)

        emoji_pattern = re.compile('['
            u'\U0001F600-\U0001F64F'  # emoticons
            u'\U0001F300-\U0001F5FF'  # symbols & pictographs
            u'\U0001F680-\U0001F6FF'  # transport & map symbols
            u'\U0001F1E0-\U0001F1FF'  # flags
            u'\U00002702-\U000027B0'
            u'\U000024C2-\U0001F251'
            u'\U0001F900-\U0001F9FF'  # supplemental symbols
            u'\U0001FA70-\U0001FAFF'
            ']+', flags=re.UNICODE)
        hashtag_pattern = re.compile(r'#\w+')

        result = emoji_pattern.sub('', result)
        result = hashtag_pattern.sub('', result)

        # 🎭 HUMANIZATION: Fix dashes and add subtle imperfections
        result = self._humanize_text(result, persona)

        # 🔧 FIX: Convert literal \n\n to actual line breaks
        result = result.replace('\\n\\n', '\n\n')
        result = result.replace(' \n\n ', '\n\n')  # Clean up extra spaces around line breaks

        result = result.strip()

        # 🎯 APPLY PLATFORM CONSTRAINTS from profile config
        thread_result = None
        if platform_constraints:
            # Apply max_length constraint with smart thread splitting
            max_length = platform_constraints.get('max_length')
            if max_length and len(result) > max_length:
                # For Twitter, use thread splitting instead of truncation
                if platform == 'twitter':
                    logger.info(f"📝 Content exceeds {max_length} chars, splitting into thread...")
                    thread_result = self.thread_splitter.split_into_thread(result, platform=platform)

                    if thread_result['is_thread']:
                        # Use threaded version
                        result = '\n\n'.join(thread_result['tweets'])
                        logger.info(f"✂️ Split into {thread_result['tweet_count']} tweets")

                        # Log any warnings
                        for warning in thread_result['warnings']:
                            logger.warning(f"⚠️ Thread: {warning}")
                    else:
                        # Fallback to truncation
                        logger.warning(f"⚠️ Could not split into thread, truncating...")
                        sentences = result[:max_length].split('.')
                        if len(sentences) > 1:
                            result = '.'.join(sentences[:-1]) + '.'
                        else:
                            result = result[:max_length].rstrip() + '...'
                else:
                    # For non-Twitter platforms, truncate at sentence boundary
                    logger.warning(f"⚠️ Content exceeds max_length ({len(result)} > {max_length}), truncating...")
                    sentences = result[:max_length].split('.')
                    if len(sentences) > 1:
                        result = '.'.join(sentences[:-1]) + '.'
                    else:
                        result = result[:max_length].rstrip() + '...'
                    logger.info(f"✂️ Truncated to {len(result)} chars")

            # Apply line break constraints
            use_line_breaks = platform_constraints.get('use_line_breaks')
            if use_line_breaks is False:
                # Remove line breaks if disabled
                result = result.replace('\n\n', ' ').replace('\n', ' ')
                # Clean up multiple spaces
                result = ' '.join(result.split())
            elif use_line_breaks is True:
                # Ensure consistent line breaks
                result = result.replace('\n\n\n', '\n\n')  # Max 2 newlines

            # Apply emoji constraints
            use_emojis = platform_constraints.get('use_emojis')
            if use_emojis is False:
                # Already removed above, but ensure
                result = emoji_pattern.sub('', result)

            # Apply hashtag constraints
            use_hashtags = platform_constraints.get('use_hashtags')
            if use_hashtags is False:
                # Already removed above, but ensure
                result = hashtag_pattern.sub('', result)

        # 🔍 VALIDATE OUTPUT LENGTH
        length_validation = self._validate_output_length(result, platform, is_thread)
        if not length_validation['valid']:
            for warning in length_validation['warnings']:
                logger.warning(warning)

        # 🔍 SCORE OUTPUT QUALITY
        quality_score = self._score_output_quality(result, persona, examples)
        if quality_score['score'] < 90:
            logger.warning(f"⚠️ Quality score: {quality_score['score']}/100 - Issues: {quality_score['issues']}")

        # 🔍 VALIDATE FACT PRESERVATION
        fact_validation = self.fact_validator.validate_preservation(
            source=original_content,
            output=result,
            critical_threshold=0.7  # 70% of critical facts must be preserved
        )

        # Add fact preservation to quality score
        if not fact_validation['valid']:
            logger.warning(f"⚠️ Fact preservation: {fact_validation['critical_preservation_rate']}% (below threshold)")
            for warning in fact_validation['warnings'][:3]:  # Show top 3 warnings
                logger.warning(f"   {warning}")

            # Penalize quality score for missing facts
            fact_penalty = (100 - fact_validation['preservation_score']) * 0.3  # Max -30 points
            quality_score['score'] = max(0, quality_score['score'] - fact_penalty)
            quality_score['issues'].append(f"Missing facts (-{int(fact_penalty)} pts)")
        else:
            logger.info(f"✅ Fact preservation: {fact_validation['preservation_score']}%")

        # 🔄 QUALITY-BASED RETRY LOGIC
        # If quality is below 70 and we haven't retried yet, try again with different approach
        MIN_QUALITY_THRESHOLD = 70
        MAX_RETRIES = 1

        if quality_score['score'] < MIN_QUALITY_THRESHOLD and _retry_attempt < MAX_RETRIES:
            logger.warning(f"🔄 Quality below threshold ({quality_score['score']} < {MIN_QUALITY_THRESHOLD}), retrying with different strategy...")

            # For retry, we'll use random example selection to get different voice examples
            # This is done by not passing the specific examples, letting smart selection pick different ones

            logger.info(f"   Retry attempt {_retry_attempt + 1}/{MAX_RETRIES}")

            # Retry the rewrite
            retry_result = await self.rewrite_analyzed_post(
                analyzed_content=analyzed_content,
                persona=persona,
                platform=platform,
                generate_variations=generate_variations,
                custom_prompt=custom_prompt,
                platform_constraints=platform_constraints,
                target_content_type=target_content_type,
                _retry_attempt=_retry_attempt + 1
            )

            # Compare quality scores and return the better result
            retry_quality = retry_result.get('quality_score', 0)

            if retry_quality > quality_score['score']:
                logger.info(f"✅ Retry improved quality: {quality_score['score']} → {retry_quality}")
                retry_result['retry_count'] = _retry_attempt + 1
                retry_result['original_quality_score'] = quality_score['score']
                return retry_result
            else:
                logger.info(f"⚠️ Retry did not improve quality ({retry_quality} ≤ {quality_score['score']}), using original")

        # Get discovery signals for metadata
        discovery_signals = analyzed_content.get('discovery_signals', {})
        content_freshness = analyzed_content.get('content_freshness', {})

        # 🎭 VOICE CONSISTENCY VALIDATION
        voice_validation = {'is_consistent': True, 'consistency_score': 100, 'issues': [], 'warnings': []}
        if self.voice_validator:
            try:
                logger.info(f"🎭 Validating voice consistency for {persona}")
                voice_validation = self.voice_validator.validate_voice(
                    text=result,
                    persona=persona,
                    return_details=True
                )

                if not voice_validation['is_consistent']:
                    logger.warning(f"⚠️ Voice consistency check failed ({voice_validation['consistency_score']:.1f}%)")
                    for issue in voice_validation['issues']:
                        logger.warning(f"  - {issue}")

                    # Get improvement suggestions
                    suggestions = self.voice_validator.get_improvement_suggestions(voice_validation, persona)
                    voice_validation['suggestions'] = suggestions

            except Exception as e:
                logger.warning(f"⚠️ Voice validation failed: {e}")

        # 📊 LOG ANALYTICS
        if self.analytics:
            try:
                self.analytics.log_rewrite({
                    "persona": persona,
                    "platform": platform,
                    "content_type": self._classify_content_type(original_content, category, topics, persona=persona),
                    "quality_score": quality_score['score'],
                    "length_valid": length_validation['valid'],
                    "examples_used": [ex.get('id') if isinstance(ex, dict) else None for ex in examples_sample] if 'examples_sample' in locals() else [],
                    "tone_detected": self._detect_content_tone(original_content),
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                })
            except Exception as e:
                logger.warning(f"Failed to log analytics: {e}")

        return {
            "persona": persona,
            "persona_name": persona_info["name"],
            "persona_emoji": persona_info["emoji"],
            "platform": platform,
            "platform_fit": platform_fit,
            "original_post_id": analyzed_content.get('post_id'),
            "original_platform": analyzed_content.get('platform'),
            "original_url": analyzed_content.get('url', ''),
            "rewritten_content": result,

            # Enhanced metadata from analyzer
            "angle_used": persona_angle.get('angle'),
            "hook_used": hook,
            "tone_used": angle_tone,
            "call_to_action": call_to_action,
            "key_points_covered": key_points,

            # Discovery signals (for scheduling/prioritization)
            "viral_potential": discovery_signals.get('viral_potential', 0),
            "author_authority": discovery_signals.get('author_authority', 'medium'),
            "trend_relevance": discovery_signals.get('trend_relevance', 'mainstream'),
            "time_sensitivity": content_freshness.get('time_sensitivity', 'evergreen'),

            # Scores
            "original_value_score": analyzed_content.get('intelligent_value_score', 0),
            "original_quality_score": analyzed_content.get('content_quality_score', 0),

            # NEW: Quality and validation
            "quality_score": quality_score['score'],
            "quality_rating": quality_score['quality'],
            "quality_issues": quality_score['issues'],
            "length_valid": length_validation['valid'],
            "length_warnings": length_validation.get('warnings', []),
            "content_length": length_validation.get('length', 0) if not is_thread else length_validation.get('max_tweet_length', 0),
            "tweet_count": length_validation.get('tweet_count', 1) if is_thread else 1,

            # Fact preservation
            "fact_preservation_score": fact_validation['preservation_score'],
            "fact_preservation_valid": fact_validation['valid'],
            "facts_preserved": fact_validation['total_facts'],
            "fact_warnings": fact_validation['warnings'],

            # Thread info (if split into thread)
            "is_thread": thread_result['is_thread'] if thread_result else False,
            "thread_tweets": thread_result['tweets'] if thread_result and thread_result['is_thread'] else [result],
            "thread_count": thread_result['tweet_count'] if thread_result else 1,

            # Voice consistency
            "voice_consistent": voice_validation['is_consistent'],
            "voice_consistency_score": voice_validation['consistency_score'],
            "voice_issues": voice_validation['issues'],
            "voice_warnings": voice_validation['warnings'],
            "voice_suggestions": voice_validation.get('suggestions', []),
            "voice_details": voice_validation.get('details', {}),

            "timestamp": datetime.now().isoformat()
        }

    async def _extract_core_ideas(
        self,
        content: str,
        analyzed_content: Dict[str, Any],
        target_platform: str = None,
        target_content_type: str = None
    ) -> str:
        """
        Stage 1: Extract core ideas from content using Gemini
        This prevents literal translation by separating extraction from writing

        Args:
            content: Original content
            analyzed_content: Analysis metadata
            target_platform: Target platform (twitter/threads/telegram) - affects extraction focus
            target_content_type: Content type (tech_news/deep_analysis/etc) - guides extraction depth
        """
        logger.info(f"📝 Stage 1: Extracting core ideas with Gemini (target: {target_platform}/{target_content_type})")

        summary = analyzed_content.get('summary', '')
        category = analyzed_content.get('category', 'General')
        key_concepts = analyzed_content.get('key_concepts') or []
        topics = analyzed_content.get('topics') or []

        # Platform-specific extraction guidance
        platform_guidance = ""
        if target_platform == 'twitter':
            platform_guidance = "\n\nEXTRACTION FOCUS FOR TWITTER: Extract punchy insights, key numbers, one-sentence takeaways. Keep it concise."
        elif target_platform == 'threads':
            platform_guidance = "\n\nEXTRACTION FOCUS FOR THREADS: Extract with context - why this matters, implications, comparisons. Include background."
        elif target_platform == 'telegram':
            platform_guidance = "\n\nEXTRACTION FOCUS FOR TELEGRAM: Extract deep analysis points, technical details, step-by-step explanations. Be thorough."

        # Content type-specific extraction depth
        depth_guidance = ""
        if target_content_type:
            if 'breaking' in target_content_type.lower() or 'news' in target_content_type.lower():
                depth_guidance = "\n\nCONTENT TYPE: News/Breaking - Focus on what happened, key facts, immediate impact."
            elif 'analysis' in target_content_type.lower() or 'deep' in target_content_type.lower():
                depth_guidance = "\n\nCONTENT TYPE: Analysis - Focus on implications, context, deeper meaning, connections to trends."
            elif 'tutorial' in target_content_type.lower() or 'guide' in target_content_type.lower():
                depth_guidance = "\n\nCONTENT TYPE: Tutorial/Guide - Focus on actionable steps, practical tips, how-to insights."

        extraction_prompt = f"""Analyze this content and extract the CORE IDEAS and KEY INSIGHTS.

Original content:
{content[:800]}

Summary: {summary}
Category: {category}
Key concepts: {', '.join(key_concepts[:5])}
Topics: {', '.join(topics[:5])}{platform_guidance}{depth_guidance}

Extract:
1. The main message/thesis (1-2 sentences)
2. 3-5 key points or insights
3. CRITICAL: ALL SPECIFIC DATA - numbers, statistics, percentages, benchmarks, costs, sizes, comparisons
   - Example: "671B parameters distilled to 1.5B, 7B, 32B"
   - Example: "Training cost $6M vs hundreds of millions for GPT-4"
   - Example: "85% accuracy on AIME, MATH, GPQA benchmarks"
   - DO NOT generalize these - keep exact numbers
4. The emotional tone or angle (e.g., critical, optimistic, sarcastic, etc.)

CRITICAL RULES:
- ONLY extract information explicitly stated in the source
- DO NOT invent product names, features, or details that aren't mentioned
- If source says "I made a tool", don't invent the tool name or detailed features
- Preserve ALL specific data points, numbers, and concrete facts
- If something isn't mentioned, don't add it

Output as a structured list of ideas with SPECIFIC DATA PRESERVED.

Core ideas:"""

        # Use LLM with fallback chain for extraction
        # (Gemini first, then Mistral, then Ollama)
        ideas = await self._call_llm(extraction_prompt, max_tokens=400, language="english")
        logger.info(f"✅ Extracted ideas: {ideas[:200]}...")
        return ideas

    async def _call_llm(self, prompt: str, max_tokens: int = 500, language: str = "russian") -> str:
        """
        Call LLM with automatic fallback chain and circuit breaker protection:
        1. Try Gemini (primary, free tier)
        2. Try Mistral (if configured and circuit breaker allows)
        3. Try local Ollama (last resort, always available)
        """

        # Try Gemini first
        result = await self._call_gemini(prompt, max_tokens)

        # If Gemini failed, try fallbacks (only if circuit breaker allows)
        if result.startswith("Error:"):
            logger.warning(f"Gemini failed: {result[:100]}")

            # Try Mistral if configured and circuit breaker allows
            if self.mistral_api_keys and self.circuit_breaker.can_call("mistral"):
                logger.info("🔄 Falling back to Mistral...")
                result = await self._call_mistral(prompt, max_tokens)

                if not result.startswith("Error:"):
                    return result
                logger.warning(f"Mistral also failed: {result[:100]}")
            elif self.mistral_api_keys:
                logger.warning("🚫 Mistral circuit breaker is OPEN, skipping fallback")

            # Last resort: try local Ollama (always available, no circuit breaker needed)
            # Use Vikhr for Russian, Qwen for English
            model = os.getenv('OLLAMA_RUSSIAN_MODEL', 'hf.co/Vikhrmodels/QVikhr-3-4B-Instruction-GGUF:latest') if language == "russian" else "qwen2.5:7b"
            logger.info(f"🔄 Falling back to local Ollama ({model})...")
            result = await self._call_ollama(prompt, max_tokens, model)

        return result

    async def _call_gemini(self, prompt: str, max_tokens: int = 500, retry_count: int = 0) -> str:
        """
        Call Gemini API for Russian content generation with:
        - Key rotation
        - Automatic retries
        - Fallback strategies
        - Better error handling
        - Circuit breaker protection
        """
        logger.info("🌟 Using Gemini 2.0 Flash for Russian content")

        if not self.gemini_api_keys:
            logger.error("No Gemini API keys configured in environment")
            return "Error: GEMINI_API_KEY not configured"

        # 🚨 CHECK CIRCUIT BREAKER FIRST
        if not self.circuit_breaker.can_call("gemini"):
            logger.error("🚫 Circuit breaker: Gemini API is OPEN (all keys exhausted)")
            return "Error: All Gemini API keys exhausted (circuit breaker open)"

        # Try each API key in rotation until one succeeds
        max_retries = len(self.gemini_api_keys)
        last_error = None
        all_errors = []
        exhausted_keys = self.circuit_breaker.get_exhausted_keys("gemini")

        for attempt in range(max_retries):
            api_key = self._get_next_gemini_key()
            key_num = (self.current_key_index - 1) % len(self.gemini_api_keys) + 1
            
            # Skip exhausted keys (tracked by circuit breaker)
            if (key_num - 1) in exhausted_keys:
                logger.debug(f"⏭️ Skipping exhausted key #{key_num} (circuit breaker)")
                continue

            try:
                async with httpx.AsyncClient() as client:
                    logger.info(f"📡 Trying API key #{key_num}/{len(self.gemini_api_keys)} (attempt {retry_count + 1})")

                    response = await client.post(
                        f"{self.gemini_url}?key={api_key}",
                        json={
                            "contents": [{
                                "parts": [{
                                    "text": prompt
                                }]
                            }],
                            "generationConfig": {
                                "temperature": 0.7,  # Lower temp for more consistent quality
                                "maxOutputTokens": max_tokens,
                                "topP": 0.9,
                                "topK": 40
                            }
                        },
                        timeout=60
                    )

                    if response.status_code == 200:
                        result = response.json()
                        candidates = result.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts:
                                text = parts[0].get("text", "").strip()
                                logger.info(f"✅ Gemini (key #{key_num}) generated {len(text)} chars")
                                # ✅ SUCCESS - record it in circuit breaker
                                self.circuit_breaker.record_success("gemini")
                                return text

                    # Rate limit or quota exceeded - try next key
                    if response.status_code in [429, 403]:
                        error_msg = f"Rate limit/quota on key #{key_num}"
                        logger.warning(f"⚠️ {error_msg}, trying next key...")
                        all_errors.append(error_msg)
                        last_error = error_msg
                        
                        # ❌ FAILURE - record it in circuit breaker
                        self.circuit_breaker.record_failure(
                            provider="gemini",
                            error_type="rate_limit",
                            api_key_index=key_num - 1
                        )

                        # If this is our last key and we haven't retried yet, wait and retry
                        # But only if we have more than 1 key (otherwise waiting won't help)
                        if attempt == max_retries - 1 and retry_count == 0 and len(self.gemini_api_keys) > 1:
                            logger.info("⏳ All keys hit limits, waiting 10s before retry...")
                            import asyncio
                            await asyncio.sleep(10)
                            return await self._call_gemini(prompt, max_tokens, retry_count + 1)
                        elif attempt == max_retries - 1 and len(self.gemini_api_keys) == 1:
                            logger.warning("🚫 Single API key hit rate limit - no retry")
                            break

                        continue

                    # Other errors
                    error_msg = f"API error {response.status_code}: {response.text[:200]}"
                    logger.error(f"Gemini error (key #{key_num}): {error_msg}")
                    all_errors.append(error_msg)
                    last_error = error_msg

                    # If only one key, return error immediately
                    if len(self.gemini_api_keys) == 1:
                        return "Error: Gemini API call failed"

                    # Otherwise try next key
                    continue

            except httpx.TimeoutException as e:
                error_msg = f"Timeout on key #{key_num}"
                logger.error(error_msg)
                all_errors.append(error_msg)
                last_error = error_msg

                # Retry with longer timeout
                if retry_count == 0:
                    logger.info("⏳ Retrying with longer timeout...")
                    return await self._call_gemini(prompt, max_tokens, retry_count + 1)

                continue

            except Exception as e:
                error_msg = f"Exception on key #{key_num}: {str(e)}"
                logger.error(error_msg)
                all_errors.append(error_msg)
                last_error = error_msg

                # If only one key, return error immediately
                if len(self.gemini_api_keys) == 1:
                    return f"Error: {e}"

                # Otherwise try next key
                continue

        # All keys failed - log detailed error summary
        logger.error(f"❌ All {len(self.gemini_api_keys)} API keys failed after {retry_count + 1} attempts")
        logger.error(f"Error summary: {all_errors}")

        # Check if ALL errors were rate limits - if so, don't waste time retrying
        all_rate_limits = all("Rate limit" in err or "quota" in err for err in all_errors)

        if all_rate_limits:
            logger.error("🚫 All API keys hit rate limits - circuit breaker will prevent further attempts")
            # Record final failure to open circuit breaker
            self.circuit_breaker.record_failure(
                provider="gemini",
                error_type="rate_limit"
            )
            return f"Error: All API keys exhausted (rate limits) - {last_error}"

        return f"Error: All API keys exhausted - {last_error}"

    async def _call_mistral(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Call Mistral API as fallback option with key rotation and circuit breaker

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text or error message
        """
        if not self.mistral_api_keys:
            return "Error: No Mistral API keys configured"

        # 🚨 CHECK CIRCUIT BREAKER FIRST
        if not self.circuit_breaker.can_call("mistral"):
            logger.error("🚫 Circuit breaker: Mistral API is OPEN (all keys exhausted)")
            return "Error: All Mistral API keys exhausted (circuit breaker open)"

        logger.info("🌟 Using Mistral AI as fallback")
        exhausted_keys = self.circuit_breaker.get_exhausted_keys("mistral")

        # Try all Mistral keys in rotation
        for key_num in range(len(self.mistral_api_keys)):
            # Skip exhausted keys
            if key_num in exhausted_keys:
                logger.debug(f"⏭️ Skipping exhausted Mistral key #{key_num + 1} (circuit breaker)")
                continue
            api_key = self.mistral_api_keys[self.current_mistral_index]
            logger.info(f"📡 Trying Mistral key #{self.current_mistral_index + 1}/{len(self.mistral_api_keys)}")

            # Rotate to next key for next call
            self.current_mistral_index = (self.current_mistral_index + 1) % len(self.mistral_api_keys)

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.mistral_url,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.mistral_model,
                            "messages": [
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.9,
                            "max_tokens": max_tokens
                        },
                        timeout=60
                    )

                    if response.status_code == 200:
                        result = response.json()
                        choices = result.get("choices", [])
                        if choices:
                            text = choices[0].get("message", {}).get("content", "").strip()
                            logger.info(f"✅ Mistral generated {len(text)} chars")
                            # ✅ SUCCESS - record it in circuit breaker
                            self.circuit_breaker.record_success("mistral")
                            return text

                    # Rate limit or error - try next key
                    if response.status_code in [429, 403]:
                        # ❌ FAILURE - record it in circuit breaker
                        self.circuit_breaker.record_failure(
                            provider="mistral",
                            error_type="rate_limit",
                            api_key_index=key_num
                        )
                    logger.warning(f"⚠️ Mistral key #{key_num + 1} failed: {response.status_code}")
                    continue

            except Exception as e:
                logger.error(f"Mistral key #{key_num + 1} exception: {e}")
                continue

        # All keys failed
        logger.error("❌ All Mistral API keys failed")
        return "Error: All Mistral API keys exhausted"

    async def _call_ollama(self, prompt: str, max_tokens: int = 500, model: str = "qwen2.5:7b") -> str:
        """Call local Ollama LLM as last-resort fallback"""
        logger.info(f"⚠️  Using local Ollama as last resort: {model}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": max_tokens
                        }
                    },
                    timeout=90
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()

                return "Error: Failed to generate content"

        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return f"Error: {e}"
    
    def get_available_personas(self) -> List[Dict[str, str]]:
        """Get list of available personas"""
        
        return [
            {
                "id": persona_id,
                "name": info["name"],
                "emoji": info["emoji"],
                "audience": info["audience"],
                "style": info["style"]
            }
            for persona_id, info in self.personas.items()
        ]
    
    async def generate_all_versions(
        self,
        content: Dict[str, Any],
        platform: str = "twitter"
    ) -> Dict[str, Dict[str, Any]]:
        """Generate versions for all personas"""
        
        logger.info(f"🎭 Generating all persona versions for {platform}")
        
        versions = {}
        
        for persona_id in self.personas.keys():
            rewritten = await self.rewrite_for_persona(content, persona_id, platform)
            versions[persona_id] = rewritten
        
        return versions


# Singleton
_rewriter = None


def get_rewriter() -> ContentRewriter:
    """Get global rewriter instance"""
    global _rewriter
    if _rewriter is None:
        _rewriter = ContentRewriter()
    return _rewriter


async def test_rewriter():
    """Test content rewriter"""
    
    print("🧪 Testing Content Rewriter\n")
    
    rewriter = get_rewriter()
    
    # Test GitHub content
    github_content = {
        "type": "github",
        "name": "openai/whisper",
        "description": "Robust Speech Recognition via Large-Scale Weak Supervision",
        "stars": 88865,
        "tldr": "State-of-the-art speech recognition with 99 language support",
        "use_cases": ["transcription", "subtitles", "voice interfaces", "accessibility"],
        "key_features": ["99 languages", "Multiple model sizes", "Easy to use", "Open source"],
        "why_matters": "Industry-leading solution • Excellent quality",
        "target_audience": ["developers", "data scientists"],
        "rewrite_angles": [
            {
                "persona": "technical",
                "angle": "Deep dive into architecture",
                "hook": "How Whisper achieves SOTA accuracy"
            },
            {
                "persona": "builder",
                "angle": "Practical applications",
                "hook": "5 ways to use Whisper in your products"
            }
        ]
    }
    
    # Test rewrite for builder persona
    print("✍️  Rewriting for: Startup Builder\n")
    
    result = await rewriter.rewrite_for_persona(github_content, "builder", "twitter")
    
    print("=" * 70)
    print(f"{result['persona_emoji']} {result['persona'].upper()} VERSION")
    print("=" * 70)
    print()
    print(result['rewritten_content'])
    print()
    print(f"Angle: {result['angle_used']}")
    print(f"Hook: {result['hook']}")
    print()
    print("✅ Rewriter working!")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_rewriter())
