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

        # Gemini API setup
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = "gemini-2.0-flash"
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"

        # Load voice patterns and opinions
        self.voice_patterns = self._load_voice_patterns()
        self.opinions = self._load_opinions()

        # Load voice examples for each persona
        self.voice_examples = self._load_voice_examples()

        # Load rewrite rules (NO HARD-CODED PROMPTS)
        self.rewrite_rules = self._load_rewrite_rules()
    
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
                "language": "english",
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
        """Load voice examples for each persona"""
        examples = {}
        config_dir = Path(__file__).parent.parent.parent / "config" / "personas"

        for persona in ["qronoya", "aspandead", "claimzilla"]:
            examples_file = config_dir / f"{persona}_examples.json"
            if examples_file.exists():
                try:
                    with open(examples_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Extract only non-empty examples
                        example_texts = [
                            ex['content'] for ex in data.get('examples', [])
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

    async def rewrite_analyzed_post(
        self,
        analyzed_content: Dict[str, Any],
        persona: str,
        platform: str = "auto"
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
        platform_fit = persona_angle.get('platform_fit', 'twitter_thread')
        if 'thread' in platform_fit:
            format_constraint = "Thread format: 3-7 tweets, each <280 chars, numbered"
        elif 'short' in platform_fit:
            format_constraint = "Single tweet: <280 chars, punchy and direct"
        elif 'linkedin' in platform_fit:
            format_constraint = "LinkedIn post: 150-300 words, professional tone"
        else:
            format_constraint = "Optimized for engagement"

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
            examples_sample = examples[:3]  # Use first 3 examples
            voice_examples_text = f"""

VOICE EXAMPLES (learn from these authentic posts by {persona_info['name']}):
{chr(10).join(f'{i+1}. {ex}' for i, ex in enumerate(examples_sample))}

Study these examples to understand:
- Natural vocabulary and phrasing
- Sentence structure and rhythm
- Tone and personality
- How this person actually writes
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
            logger.info("🔄 Using TWO-STAGE pipeline: Qwen extraction → Vikhr writing")

            # Stage 1: Extract core ideas using Qwen (English-native)
            extracted_ideas = await self._extract_core_ideas(original_content, analyzed_content)

            # Stage 2: Write from ideas using Vikhr (Russian-native)
            logger.info("✍️  Stage 2: Writing in Russian with Vikhr from extracted ideas")

            prompt = f"""You are {persona_info['name']}, writing a social media post in RUSSIAN.

CORE IDEAS TO EXPRESS (extracted from original content):
{extracted_ideas}

IMPORTANT: These are just IDEAS. Write them in YOUR OWN WORDS in {persona_info['name']}'s voice.
Do NOT translate literally. Express these concepts naturally in Russian.

TARGET:
- Platform: {platform}
- Tone: {angle_tone}
- Audience: {target_audience}
- Call-to-Action: {call_to_action}
- Format: {format_constraint}
{language_instruction}

VOICE PATTERNS (write like this):
Vocabulary: {', '.join(vocabulary.get('preferred_words', [])[:10])}
Opening phrases: {', '.join(sentence_patterns.get('opening_phrases', [])[:3])}
Quirks: {', '.join(quirks[:3])}
{voice_examples_text}
{opinions_text}

{self._build_rewrite_instructions(persona)}

Write the post in Russian:"""

            result = await self._call_llm(prompt, max_tokens=800, language="russian")

        else:
            # SINGLE-STAGE FOR ENGLISH (as before)
            logger.info("📝 Using SINGLE-STAGE pipeline for English")

            prompt = f"""Rewrite this social media post as {persona_info['name']} for {platform}.

ORIGINAL POST (extract the IDEA, don't copy the text):
Category: {category}
Topics: {', '.join(topics)}
Key Concepts: {', '.join(key_concepts)}
Content: {original_content}

REWRITE ANGLE:
Angle: {persona_angle.get('angle', '')}
Hook: {hook}
Key Points:
{chr(10).join(f"  • {point}" for point in key_points)}

TARGET:
- Tone: {angle_tone}
- Audience: {target_audience}
- Call-to-Action: {call_to_action}
- Format: {format_constraint}
{language_instruction}

VOICE PATTERNS (mimic these):
Vocabulary: {', '.join(vocabulary.get('preferred_words', [])[:10])}
Opening phrases: {', '.join(sentence_patterns.get('opening_phrases', [])[:3])}
Quirks: {', '.join(quirks[:3])}
{voice_examples_text}
{opinions_text}

{self._build_rewrite_instructions(persona)}

Rewritten post:"""

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
        result = result.strip()

        # Get discovery signals for metadata
        discovery_signals = analyzed_content.get('discovery_signals', {})
        content_freshness = analyzed_content.get('content_freshness', {})

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

            "timestamp": datetime.now().isoformat()
        }

    async def _extract_core_ideas(self, content: str, analyzed_content: Dict[str, Any]) -> str:
        """
        Stage 1: Extract core ideas from content using Qwen (English-native)
        This prevents literal translation by separating extraction from writing
        """
        logger.info("📝 Stage 1: Extracting core ideas with Qwen")

        summary = analyzed_content.get('summary', '')
        category = analyzed_content.get('category', 'General')
        key_concepts = analyzed_content.get('key_concepts') or []
        topics = analyzed_content.get('topics') or []

        extraction_prompt = f"""Analyze this content and extract the CORE IDEAS and KEY INSIGHTS.

Original content:
{content[:800]}

Summary: {summary}
Category: {category}
Key concepts: {', '.join(key_concepts[:5])}
Topics: {', '.join(topics[:5])}

Extract:
1. The main message/thesis (1-2 sentences)
2. 3-5 key points or insights
3. Any important data, examples, or comparisons mentioned
4. The emotional tone or angle (e.g., critical, optimistic, sarcastic, etc.)

Output as a structured list of ideas, NOT a rewrite. Focus on WHAT is being said, not HOW it's said.

Core ideas:"""

        ideas = await self._call_llm(extraction_prompt, max_tokens=400, language="english")
        logger.info(f"✅ Extracted ideas: {ideas[:200]}...")
        return ideas

    async def _call_llm(self, prompt: str, max_tokens: int = 500, language: str = "english") -> str:
        """Call LLM - uses Gemini for Russian, Qwen for English"""

        # Use Gemini for Russian (free tier, better quality)
        if language == "russian":
            return await self._call_gemini(prompt, max_tokens)
        else:
            # Use local Qwen for English
            return await self._call_ollama(prompt, max_tokens, "qwen2.5:7b")

    async def _call_gemini(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Gemini API for Russian content generation"""
        logger.info("🌟 Using Gemini 1.5 Flash for Russian content")

        if not self.gemini_api_key:
            logger.error("GEMINI_API_KEY not set in environment")
            return "Error: GEMINI_API_KEY not configured"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gemini_url}?key={self.gemini_api_key}",
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
                        "generationConfig": {
                            "temperature": 0.7,
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
                            logger.info(f"✅ Gemini generated {len(text)} chars")
                            return text

                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return "Error: Gemini API call failed"

        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return f"Error: {e}"

    async def _call_ollama(self, prompt: str, max_tokens: int = 500, model: str = "qwen2.5:7b") -> str:
        """Call local Ollama LLM"""
        logger.info(f"Using Ollama model: {model}")

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
