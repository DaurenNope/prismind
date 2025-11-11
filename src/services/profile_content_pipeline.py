"""
Profile-Based Content Pipeline

Flexible system for managing content across multiple platforms for any profile/persona.
Each profile has its own configuration for platforms, languages, prompts, and routing logic.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProfileContentPipeline:
    """
    Flexible content pipeline that works with any profile configuration.

    Features:
    - Load profile configs from config/profiles/
    - Route content to platforms based on time sensitivity
    - Select appropriate prompts based on platform + content type
    - Handle platform-specific formatting (language, length, markdown, etc.)
    - Enrich Reddit posts with comment context
    """

    def __init__(self, profile_key: str):
        """
        Initialize pipeline for a specific profile

        Args:
            profile_key: Profile identifier (e.g., 'qronoya', 'aspandead')
        """
        self.profile_key = profile_key
        self.config = self._load_profile_config(profile_key)
        self.profile_name = self.config['display_name']

        logger.info(f"✅ Initialized ProfileContentPipeline for {self.profile_name}")

    def _load_profile_config(self, profile_key: str) -> Dict:
        """Load profile configuration from JSON"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'profiles' / f'{profile_key}.json'

        if not config_path.exists():
            raise FileNotFoundError(f"Profile config not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info(f"📄 Loaded config for {config['display_name']}")
        return config

    def get_enabled_platforms(self) -> List[str]:
        """Get list of enabled platforms for this profile"""
        return [
            platform
            for platform, settings in self.config['platforms'].items()
            if settings.get('enabled', False)
        ]

    def route_content(self, relevance_window: str) -> List[str]:
        """
        Determine which platforms to post to based on time sensitivity

        Args:
            relevance_window: One of 'same-day', '24-72h', 'this-week', 'evergreen'

        Returns:
            List of platform keys in priority order
        """
        routing = self.config.get('content_routing', {}).get(relevance_window, {})
        platforms = routing.get('platforms', [])

        # Filter to only enabled platforms
        enabled = self.get_enabled_platforms()
        platforms = [p for p in platforms if p in enabled]

        logger.info(f"📍 Routing '{relevance_window}' content to: {platforms}")
        return platforms

    def select_prompt_template(
        self,
        platform: str,
        content_type: str,
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Select the appropriate prompt template

        Args:
            platform: Platform key (e.g., 'twitter', 'threads', 'telegram')
            content_type: Type of content (e.g., 'tech_news', 'tool_review')
            language: Language code (e.g., 'ru', 'en') - auto-detected if None

        Returns:
            Prompt template string or None if not found
        """
        platform_config = self.config['platforms'].get(platform, {})

        # Auto-detect language from platform config if not provided
        if language is None:
            language = platform_config.get('language', 'en')

        # Build prompt template key: platform_language_contenttype
        template_key = f"{platform}_{language}_{content_type}"

        # Try to find template
        template = self.config.get('prompt_templates', {}).get(template_key)

        if not template:
            # Try fallback without content type
            template_key_fallback = f"{platform}_{language}"
            template = self.config.get('prompt_templates', {}).get(template_key_fallback)

        if template:
            logger.info(f"📝 Selected prompt template: {template_key}")
        else:
            logger.warning(f"⚠️  No prompt template found for {template_key}")

        return template

    def format_prompt(
        self,
        template: str,
        source_content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Fill in prompt template with content and metadata

        Args:
            template: Prompt template string with placeholders
            source_content: Original content to rewrite
            metadata: Post metadata (category, topics, etc.)

        Returns:
            Formatted prompt ready for LLM
        """
        # Get voice guidelines
        voice_russian = self.config['voice_guidelines'].get('russian', '')
        voice_english = self.config['voice_guidelines'].get('english', '')
        voice_general = self.config['voice_guidelines'].get('general', '')

        # Build replacement dict
        replacements = {
            'profile_name': self.profile_name,
            'profile_key': self.profile_key,
            'source_content': source_content,
            'voice_russian': voice_russian,
            'voice_english': voice_english,
            'voice_general': voice_general,
            'category': metadata.get('category', 'general'),
            'topics': ', '.join(metadata.get('topics', [])),
            'key_concepts': ', '.join(metadata.get('key_concepts', [])),
            'title': metadata.get('title', ''),
            'content_type': metadata.get('content_type', ''),
        }

        # Fill template
        prompt = template
        for key, value in replacements.items():
            prompt = prompt.replace(f'{{{key}}}', str(value))

        return prompt

    def get_platform_constraints(self, platform: str) -> Dict[str, Any]:
        """
        Get formatting constraints for a platform

        Args:
            platform: Platform key

        Returns:
            Dict with max_length, use_markdown, use_emojis, etc.
        """
        platform_config = self.config['platforms'].get(platform, {})
        return platform_config.get('format_preferences', {})

    def should_include_reddit_comments(self) -> bool:
        """Check if Reddit comments should be included"""
        return self.config.get('source_preferences', {}).get('reddit', {}).get('include_comments', False)

    def get_reddit_comment_settings(self) -> Dict[str, int]:
        """Get Reddit comment extraction settings"""
        reddit_prefs = self.config.get('source_preferences', {}).get('reddit', {})
        return {
            'min_score': reddit_prefs.get('min_comment_score', 10),
            'max_comments': reddit_prefs.get('max_comments', 5)
        }

    def prepare_content_for_rewrite(
        self,
        post: Dict[str, Any],
        platform: str,
        content_type: str
    ) -> Dict[str, Any]:
        """
        Prepare post content for rewriting

        Args:
            post: Post dict from usable_posts table
            platform: Target platform
            content_type: Content type for this rewrite

        Returns:
            Dict ready for rewriter with prompt, constraints, metadata
        """
        # Get prompt template
        template = self.select_prompt_template(platform, content_type)

        if not template:
            raise ValueError(f"No prompt template for {platform}/{content_type}")

        # Prepare metadata
        metadata = {
            'category': post.get('category', ''),
            'topics': post.get('tags', []),
            'key_concepts': post.get('key_concepts', []),
            'title': post.get('title', ''),
            'content_type': content_type,
            'platform': post.get('platform', ''),
            'source_url': post.get('url', ''),
        }

        # Format prompt
        prompt = self.format_prompt(
            template=template,
            source_content=post['content'],
            metadata=metadata
        )

        # Get platform constraints
        constraints = self.get_platform_constraints(platform)

        return {
            'prompt': prompt,
            'constraints': constraints,
            'metadata': metadata,
            'profile_key': self.profile_key,
            'profile_name': self.profile_name,
            'target_platform': platform,
            'content_type': content_type,
            'source_post_id': post.get('post_id'),
        }

    def get_content_types_for_platform(self, platform: str) -> List[str]:
        """Get supported content types for a platform"""
        platform_config = self.config['platforms'].get(platform, {})
        return platform_config.get('content_types', [])

    def match_content_type(
        self,
        post_category: str,
        platform: str
    ) -> Optional[str]:
        """
        Match post category to platform-specific content type

        Args:
            post_category: Category from usable_posts (e.g., 'tech_trend')
            platform: Target platform

        Returns:
            Content type for this platform or None
        """
        supported_types = self.get_content_types_for_platform(platform)

        # Simple mapping (can be enhanced with more sophisticated matching)
        category_mapping = {
            'tech_trend': ['tech_news', 'design_news', 'breaking_news'],
            'tool_review': ['tool_review', 'tool_showcase', 'tool_comparison'],
            'ai_news': ['tech_news', 'breaking_news', 'ai_discussion'],
            'dev_insight': ['dev_insight', 'creative_insight', 'quick_take'],
            'tutorial': ['tutorial_guide', 'design_tip'],
            'industry_analysis': ['deep_analysis', 'design_discussion'],
        }

        possible_types = category_mapping.get(post_category, [])

        # Return first match
        for content_type in possible_types:
            if content_type in supported_types:
                return content_type

        # Fallback to first supported type
        if supported_types:
            return supported_types[0]

        return None

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get summary of pipeline configuration"""
        return {
            'profile_key': self.profile_key,
            'profile_name': self.profile_name,
            'description': self.config.get('description', ''),
            'enabled_platforms': self.get_enabled_platforms(),
            'total_prompt_templates': len(self.config.get('prompt_templates', {})),
            'content_routing': self.config.get('content_routing', {}),
        }


def list_available_profiles() -> List[Dict[str, str]]:
    """
    List all available profile configurations

    Returns:
        List of dicts with profile_key, display_name, description
    """
    profiles_dir = Path(__file__).parent.parent.parent / 'config' / 'profiles'

    if not profiles_dir.exists():
        logger.warning(f"Profiles directory not found: {profiles_dir}")
        return []

    profiles = []

    for config_file in profiles_dir.glob('*.json'):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            profiles.append({
                'profile_key': config.get('profile_key', config_file.stem),
                'display_name': config.get('display_name', config_file.stem),
                'description': config.get('description', ''),
                'enabled_platforms': [
                    p for p, s in config.get('platforms', {}).items()
                    if s.get('enabled', False)
                ]
            })
        except Exception as e:
            logger.error(f"Error loading profile {config_file}: {e}")

    return profiles


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("="*80)
    print("PROFILE CONTENT PIPELINE - DEMO")
    print("="*80)

    # List available profiles
    print("\n📋 Available Profiles:\n")
    for profile in list_available_profiles():
        print(f"  • {profile['display_name']} ({profile['profile_key']})")
        print(f"    {profile['description']}")
        print(f"    Platforms: {', '.join(profile['enabled_platforms'])}")
        print()

    # Test with qronoya
    print("="*80)
    print("Testing with Qronoya profile:")
    print("="*80)

    pipeline = ProfileContentPipeline('qronoya')

    # Show summary
    summary = pipeline.get_pipeline_summary()
    print(f"\n✅ Loaded: {summary['profile_name']}")
    print(f"   Description: {summary['description']}")
    print(f"   Enabled platforms: {summary['enabled_platforms']}")
    print(f"   Prompt templates: {summary['total_prompt_templates']}")

    # Test routing
    print("\n📍 Content Routing:")
    for window in ['same-day', '24-72h', 'this-week', 'evergreen']:
        platforms = pipeline.route_content(window)
        print(f"   {window:12} → {platforms}")

    # Test prompt selection
    print("\n📝 Prompt Template Selection:")
    test_cases = [
        ('twitter', 'breaking_news'),
        ('threads', 'tech_news'),
        ('telegram', 'deep_analysis'),
    ]

    for platform, content_type in test_cases:
        template = pipeline.select_prompt_template(platform, content_type)
        if template:
            preview = template[:100].replace('\n', ' ')
            print(f"   {platform}/{content_type}: {preview}...")
        else:
            print(f"   {platform}/{content_type}: NOT FOUND")

    # Test content preparation
    print("\n🔧 Content Preparation:")
    sample_post = {
        'post_id': 'test123',
        'content': 'Sample tech news about AI breakthroughs',
        'category': 'tech_trend',
        'tags': ['ai', 'ml', 'research'],
        'key_concepts': ['neural networks', 'transformers'],
        'title': 'New AI Model Released',
        'platform': 'twitter',
        'url': 'https://example.com/post'
    }

    prepared = pipeline.prepare_content_for_rewrite(
        post=sample_post,
        platform='twitter',
        content_type='breaking_news'
    )

    print(f"   Target: {prepared['target_platform']}")
    print(f"   Content type: {prepared['content_type']}")
    print(f"   Constraints: {prepared['constraints']}")
    print(f"   Prompt preview: {prepared['prompt'][:150]}...")

    print("\n" + "="*80)
    print("✅ Pipeline test complete!")
    print("="*80)
