"""
AI Profile Onboarding Wizard

Conversational AI that interviews users and generates complete profile configurations.
This is the "selling point" feature that makes profile setup accessible to non-technical users.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key:
    genai.configure(api_key=gemini_key)


@dataclass
class WizardState:
    """Tracks the state of the wizard interview"""
    step: int = 1
    project_name: str = ""
    project_description: str = ""
    target_audience: str = ""
    unique_value: str = ""

    # Voice & Style
    tone_tags: List[str] = None
    example_posts: List[str] = None
    avoid_phrases: List[str] = None
    voice_description: str = ""

    # Platforms & Content
    platforms: List[str] = None
    platform_frequencies: Dict[str, str] = None
    content_topics: List[str] = None

    # Engagement
    auto_reply: bool = False
    reply_strategy: str = ""

    # Generated
    profile_key: str = ""
    voice_guidelines: Dict[str, str] = None
    prompt_templates: Dict[str, str] = None

    def __post_init__(self):
        if self.tone_tags is None:
            self.tone_tags = []
        if self.example_posts is None:
            self.example_posts = []
        if self.avoid_phrases is None:
            self.avoid_phrases = []
        if self.platforms is None:
            self.platforms = []
        if self.platform_frequencies is None:
            self.platform_frequencies = {}
        if self.content_topics is None:
            self.content_topics = []
        if self.voice_guidelines is None:
            self.voice_guidelines = {}
        if self.prompt_templates is None:
            self.prompt_templates = {}


class ProfileWizard:
    """AI-powered conversational wizard for creating profile configurations"""

    def __init__(self):
        model_name = os.getenv('ANALYZER_GEMINI_MODEL', 'gemini-2.0-flash-exp')
        self.model = genai.GenerativeModel(model_name)

    def get_step_prompt(self, step: int, state: WizardState) -> str:
        """Get the AI prompt for a specific wizard step"""

        if step == 1:
            return """You are a friendly onboarding assistant helping someone set up their social media profile.

Your goal: Learn about their project in a conversational way.

Ask 3 questions, one at a time:
1. "What's your project about? Tell me what you're building."
2. "Who are you trying to reach? Describe your target audience."
3. "What makes you different? What's your unique angle or value proposition?"

Keep it casual and friendly. Don't use corporate jargon. Make them feel comfortable."""

        elif step == 2:
            return f"""You are a friendly onboarding assistant. You've learned about their project:
- Project: {state.project_description}
- Audience: {state.target_audience}
- Unique value: {state.unique_value}

Now help them define their voice and style.

Guide them through:
1. Show them tone options and ask which fit their vibe:
   [Technical] [Casual] [Professional] [Edgy] [Data-driven] [Storyteller] [Memey] [Serious]

2. Ask them to share 2-3 example posts they like from other accounts (can be URLs or paste the text)

3. Ask what they should NEVER sound like (corporate jargon? hype language? overly formal?)

Extract their voice preferences in a natural conversation."""

        elif step == 3:
            return f"""You are a friendly onboarding assistant. You know their project and voice style.

Now help them set up platforms and content.

Ask:
1. "Which platforms do you want to use?"
   Options: Twitter, Threads, LinkedIn, Telegram, Instagram

2. For each selected platform: "How often do you want to post on [platform]?"
   Options: Daily, 2-3x daily, Few times a week, Weekly

3. "What topics should I write about for you?"
   Based on their project ({state.project_description}), suggest 10-15 topic ideas.
   Let them review, edit, add more.

Keep it conversational and helpful."""

        elif step == 4:
            return f"""You are a friendly onboarding assistant. Final step!

Help them set up their engagement strategy.

Ask:
1. "Do you want to automatically reply to relevant conversations in your niche?"

2. If yes: "What types of posts should I reply to?"
   Examples: Questions about [their topic], discussions about [competitor],
   people asking for recommendations, etc.

Keep it simple and actionable."""

        return ""

    async def process_user_input(self, user_message: str, state: WizardState) -> Dict[str, Any]:
        """
        Process user input for the current wizard step.
        Returns: {
            'ai_response': str,  # What to show the user
            'extracted_data': dict,  # Structured data extracted
            'next_step': int,  # Next step number (or same if need more info)
            'complete': bool  # Whether the step is complete
        }
        """

        system_prompt = self.get_step_prompt(state.step, state)

        # Add extraction instructions based on step
        extraction_prompt = self._get_extraction_instructions(state.step)

        # Build full prompt for Gemini
        full_prompt = f"{system_prompt}\n\n{extraction_prompt}\n\nUser: {user_message}"

        response = self.model.generate_content(full_prompt)

        ai_text = response.text

        # Extract structured data from the response
        extracted = self._extract_data_from_response(ai_text, state.step, user_message)

        # Determine if step is complete
        complete = self._is_step_complete(state.step, extracted)
        next_step = state.step + 1 if complete else state.step

        return {
            'ai_response': ai_text,
            'extracted_data': extracted,
            'next_step': next_step,
            'complete': complete
        }

    def _get_extraction_instructions(self, step: int) -> str:
        """Get instructions for what data to extract from the conversation"""

        if step == 1:
            return """After the conversation, extract:
- project_name (short name)
- project_description (what they're building)
- target_audience (who they're targeting)
- unique_value (what makes them different)

Format your response as natural conversation, but end with a JSON block:
```json
{
  "project_name": "...",
  "project_description": "...",
  "target_audience": "...",
  "unique_value": "..."
}
```"""

        elif step == 2:
            return """After the conversation, extract:
- tone_tags (list of selected tone words)
- example_posts (list of post texts or URLs they shared)
- avoid_phrases (list of things to avoid)
- voice_description (summary of their desired voice)

End your response with a JSON block:
```json
{
  "tone_tags": ["casual", "data-driven"],
  "example_posts": ["...", "..."],
  "avoid_phrases": ["corporate jargon", "hype language"],
  "voice_description": "..."
}
```"""

        elif step == 3:
            return """After the conversation, extract:
- platforms (list of platform names)
- platform_frequencies (dict of platform -> frequency)
- content_topics (list of topic strings)

End your response with a JSON block:
```json
{
  "platforms": ["twitter", "threads"],
  "platform_frequencies": {"twitter": "2-3x daily", "threads": "daily"},
  "content_topics": ["AI trends", "tool reviews", ...]
}
```"""

        elif step == 4:
            return """After the conversation, extract:
- auto_reply (boolean)
- reply_strategy (description of what to reply to)

End your response with a JSON block:
```json
{
  "auto_reply": true,
  "reply_strategy": "Reply to questions about DeFi, discussions about competitors, people asking for yield optimization advice"
}
```"""

        return ""

    def _extract_data_from_response(self, ai_response: str, step: int, user_input: str) -> dict:
        """Extract structured data from AI response"""

        # Look for JSON block in response
        if "```json" in ai_response:
            json_start = ai_response.find("```json") + 7
            json_end = ai_response.find("```", json_start)
            json_str = ai_response[json_start:json_end].strip()

            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Fallback: basic extraction from user input
        return self._fallback_extraction(user_input, step)

    def _fallback_extraction(self, user_input: str, step: int) -> dict:
        """Fallback extraction if JSON parsing fails"""

        if step == 1:
            return {
                "project_description": user_input,
                "target_audience": "",
                "unique_value": ""
            }
        elif step == 2:
            return {
                "tone_tags": [],
                "example_posts": [user_input] if len(user_input) > 50 else [],
                "avoid_phrases": [],
                "voice_description": user_input
            }
        elif step == 3:
            return {
                "platforms": [],
                "platform_frequencies": {},
                "content_topics": []
            }
        elif step == 4:
            return {
                "auto_reply": "yes" in user_input.lower(),
                "reply_strategy": user_input
            }

        return {}

    def _is_step_complete(self, step: int, extracted: dict) -> bool:
        """Check if a step has enough information to proceed"""

        if step == 1:
            return bool(extracted.get('project_description'))
        elif step == 2:
            return bool(extracted.get('tone_tags') or extracted.get('voice_description'))
        elif step == 3:
            return bool(extracted.get('platforms'))
        elif step == 4:
            return 'auto_reply' in extracted

        return False

    async def generate_profile_config(self, state: WizardState) -> dict:
        """
        Generate the complete profile configuration from wizard state.
        This is the magic - converts conversational data into a working config.
        """

        # Generate profile key from project name
        profile_key = self._generate_profile_key(state.project_name or state.project_description)

        # Use AI to generate voice guidelines
        voice_guidelines = await self._generate_voice_guidelines(state)

        # Use AI to expand content topics
        content_topics = await self._expand_content_topics(state)

        # Generate prompt templates for each platform
        prompt_templates = await self._generate_prompt_templates(state, voice_guidelines)

        # Build the complete config
        config = {
            "profile_key": profile_key,
            "display_name": state.project_name or profile_key.title(),
            "description": state.project_description,
            "platforms": self._build_platform_config(state),
            "content_routing": self._build_content_routing(state),
            "source_preferences": {},
            "voice_guidelines": voice_guidelines,
            "prompt_templates": prompt_templates,
            "content_topics": content_topics,
            "reply_strategy": {
                "enabled": state.auto_reply,
                "strategy": state.reply_strategy
            }
        }

        return config

    def _generate_profile_key(self, name: str) -> str:
        """Generate a valid profile key from project name"""
        # Convert to lowercase, replace spaces with underscores, remove special chars
        key = name.lower().strip()
        key = ''.join(c if c.isalnum() or c == ' ' else '' for c in key)
        key = key.replace(' ', '_')
        return key[:30]  # Limit length

    async def _generate_voice_guidelines(self, state: WizardState) -> dict:
        """Use AI to generate comprehensive voice guidelines"""

        prompt = f"""Based on this information about a social media profile, generate comprehensive voice guidelines.

Project: {state.project_description}
Target audience: {state.target_audience}
Tone preferences: {', '.join(state.tone_tags)}
Example posts they like: {state.example_posts[:2] if state.example_posts else 'None provided'}
Things to avoid: {', '.join(state.avoid_phrases)}

Generate voice guidelines with:
1. General voice description (2-3 sentences)
2. Specific do's and don'ts
3. Tone characteristics
4. Language style

Return ONLY a JSON object:
{{
  "general": "overall voice description",
  "dos": ["do this", "do that"],
  "donts": ["don't do this", "don't do that"],
  "tone": "tone description",
  "style": "style description"
}}"""

        response = self.model.generate_content(prompt)

        response_text = response.text

        # Extract JSON
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        else:
            json_str = response_text

        try:
            return json.loads(json_str)
        except:
            return {
                "general": state.voice_description or "Professional yet approachable voice",
                "dos": state.tone_tags,
                "donts": state.avoid_phrases
            }

    async def _expand_content_topics(self, state: WizardState) -> list:
        """Use AI to expand content topics to 50-100 items"""

        prompt = f"""Based on this project, generate 50-100 specific content topics for social media posts.

Project: {state.project_description}
Target audience: {state.target_audience}
Initial topics: {', '.join(state.content_topics[:10]) if state.content_topics else 'None'}

Generate diverse topics covering:
- Product features and updates
- Industry trends and news
- Educational content for the audience
- Use cases and examples
- Comparisons and analysis
- Tips and best practices
- Behind-the-scenes
- Community and engagement

Return ONLY a JSON array of topic strings:
["topic 1", "topic 2", ...]"""

        response = self.model.generate_content(prompt)

        response_text = response.text

        # Extract JSON array
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        else:
            json_str = response_text

        try:
            topics = json.loads(json_str)
            return topics if isinstance(topics, list) else state.content_topics
        except:
            return state.content_topics or []

    async def _generate_prompt_templates(self, state: WizardState, voice_guidelines: dict) -> dict:
        """Generate prompt templates for each platform + language + content type"""

        templates = {}

        # Common content types
        content_types = ["news", "insight", "tutorial", "announcement", "discussion"]

        for platform in state.platforms:
            # Determine languages (default to English)
            languages = ["en"]

            for lang in languages:
                for content_type in content_types:
                    template_key = f"{platform}_{lang}_{content_type}"

                    # Generate template using AI
                    template = await self._generate_single_template(
                        platform, lang, content_type, state, voice_guidelines
                    )

                    templates[template_key] = template

        return templates

    async def _generate_single_template(
        self, platform: str, lang: str, content_type: str,
        state: WizardState, voice_guidelines: dict
    ) -> str:
        """Generate a single prompt template"""

        prompt = f"""Create a prompt template for a social media rewriter.

Platform: {platform}
Language: {lang}
Content type: {content_type}
Project: {state.project_description}
Voice: {voice_guidelines.get('general', '')}

The template should:
1. Instruct the AI to rewrite content in the profile's voice
2. Include placeholders: {{profile_name}}, {{source_content}}, {{topics}}
3. Specify platform-specific formatting (length, style)
4. Emphasize the voice guidelines

Return ONLY the prompt template text (no JSON, no explanation)."""

        response = self.model.generate_content(prompt)

        return response.text.strip()

    def _build_platform_config(self, state: WizardState) -> dict:
        """Build platform configuration from wizard state"""

        platform_config = {}

        for platform in state.platforms:
            frequency = state.platform_frequencies.get(platform, "daily")

            # Map frequency to standardized format
            freq_map = {
                "daily": "daily",
                "2-3x daily": "2-3x_daily",
                "few times a week": "3x_weekly",
                "weekly": "weekly"
            }

            platform_config[platform.lower()] = {
                "enabled": True,
                "language": "en",
                "post_frequency": freq_map.get(frequency.lower(), "daily"),
                "content_types": ["news", "insight", "tutorial", "announcement"],
                "format_preferences": {
                    "max_length": 280 if platform.lower() == "twitter" else 500,
                    "use_line_breaks": True,
                    "use_emojis": "casual" in state.tone_tags or "memey" in state.tone_tags,
                    "use_hashtags": True,
                    "use_markdown": platform.lower() in ["telegram", "linkedin"]
                }
            }

        return platform_config

    def _build_content_routing(self, state: WizardState) -> dict:
        """Build content routing rules"""

        platforms = [p.lower() for p in state.platforms]

        return {
            "same-day": {
                "platforms": platforms[:2] if len(platforms) > 2 else platforms
            },
            "24-72h": {
                "platforms": platforms
            },
            "this-week": {
                "platforms": platforms
            },
            "evergreen": {
                "platforms": platforms
            }
        }
