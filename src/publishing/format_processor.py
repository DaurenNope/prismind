#!/usr/bin/env python3
"""
Format Processor for Platform-Specific Content Formatting

Handles post-processing of LLM output to ensure platform compliance:
- Length validation and trimming
- Thread parsing and formatting
- Platform-specific constraints
- Metadata generation
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class FormatProcessor:
    """Post-process LLM output to ensure platform compliance"""

    def __init__(self, platform_configs: Dict[str, Any] = None):
        """
        Initialize format processor

        Args:
            platform_configs: Dict of platform configurations
                             If None, loads from config/platform_formats.json
        """
        if platform_configs is None:
            self.platform_configs = self._load_platform_configs()
        else:
            self.platform_configs = platform_configs

    def _load_platform_configs(self) -> Dict[str, Any]:
        """Load platform configurations from JSON"""
        try:
            config_dir = Path(__file__).parent.parent.parent / "config"
            config_file = config_dir / "platform_formats.json"

            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                    logger.info(f"✅ Loaded platform configs for {len(configs)} platforms")
                    return configs
            else:
                logger.warning(f"Platform config not found at {config_file}")
                return self._get_default_configs()
        except Exception as e:
            logger.error(f"Error loading platform configs: {e}")
            return self._get_default_configs()

    def _get_default_configs(self) -> Dict[str, Any]:
        """Fallback default configs"""
        return {
            "twitter": {
                "constraints": {"max_length": 280},
                "formats": {"single": {"max_chars": 280, "guidance": "Single tweet"}}
            },
            "threads": {
                "constraints": {"max_length": 500},
                "formats": {"single": {"max_chars": 500, "guidance": "Single post"}}
            }
        }

    def process(
        self,
        content: str,
        platform: str,
        format_type: str = "single"
    ) -> Dict[str, Any]:
        """
        Process raw LLM output into platform-compliant format

        Args:
            content: Raw LLM output
            platform: Target platform (twitter, threads, linkedin, etc.)
            format_type: Format type (single, thread, etc.)

        Returns:
            {
                "content": formatted_content,
                "format": "single" | "thread",
                "parts": [...],  # For threads
                "warnings": [...],  # If truncated, etc.
                "metadata": {
                    "original_length": int,
                    "final_length": int,
                    "was_trimmed": bool,
                    "platform": str,
                    "format_type": str
                }
            }
        """
        if platform not in self.platform_configs:
            logger.warning(f"Unknown platform '{platform}', using default processing")
            return self._default_process(content)

        platform_config = self.platform_configs[platform]
        format_config = platform_config['formats'].get(format_type, platform_config['formats']['single'])

        original_length = len(content)
        warnings = []

        # Step 1: Detect if content is a thread
        is_thread, thread_parts = self._detect_thread(content)

        if is_thread and format_type == "thread":
            # Process as thread
            result = self._process_thread(thread_parts, platform, format_config)
        else:
            # Process as single post
            result = self._process_single(content, platform, format_config)

        # Add metadata
        result['metadata'] = {
            "original_length": original_length,
            "final_length": len(result['content']),
            "was_trimmed": result.get('was_trimmed', False),
            "platform": platform,
            "format_type": result['format']
        }

        logger.info(f"📏 Formatted for {platform}: {original_length} → {result['metadata']['final_length']} chars")

        return result

    def _detect_thread(self, content: str) -> Tuple[bool, List[str]]:
        """
        Detect if content is formatted as a thread

        Returns:
            (is_thread, thread_parts)
        """
        # Pattern: "1/\nContent\n\n2/\nContent"
        thread_pattern = r'^(\d+)/\s*\n(.+?)(?=\n\n\d+/|\Z)'
        matches = re.findall(thread_pattern, content, re.MULTILINE | re.DOTALL)

        if matches and len(matches) >= 2:
            parts = [match[1].strip() for match in matches]
            return True, parts

        return False, []

    def _process_single(
        self,
        content: str,
        platform: str,
        format_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process as single post"""
        max_chars = format_config.get('max_chars', 500)
        content = content.strip()

        was_trimmed = False
        if len(content) > max_chars:
            logger.warning(f"⚠️ Content exceeds {max_chars} chars, trimming...")
            content = self.smart_trim(content, max_chars)
            was_trimmed = True

        return {
            "content": content,
            "format": "single",
            "parts": [content],
            "warnings": ["Content was trimmed to fit platform limits"] if was_trimmed else [],
            "was_trimmed": was_trimmed
        }

    def _process_thread(
        self,
        parts: List[str],
        platform: str,
        format_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process as thread"""
        max_chars_per = format_config.get('max_chars_per_tweet', format_config.get('max_chars_per_post', 280))
        max_tweets = format_config.get('max_tweets', format_config.get('max_posts', 10))

        processed_parts = []
        warnings = []
        was_trimmed = False

        # Trim parts if needed
        for i, part in enumerate(parts[:max_tweets]):
            if len(part) > max_chars_per:
                logger.warning(f"⚠️ Thread part {i+1} exceeds {max_chars_per} chars, trimming...")
                part = self.smart_trim(part, max_chars_per)
                was_trimmed = True
                warnings.append(f"Part {i+1} was trimmed to fit")

            processed_parts.append(part)

        if len(parts) > max_tweets:
            warnings.append(f"Thread truncated to {max_tweets} parts (was {len(parts)})")

        # Format thread with numbering
        numbering_format = format_config.get('numbering_format', '{number}/\n{content}')
        formatted_thread = []

        for i, part in enumerate(processed_parts, 1):
            formatted = numbering_format.format(number=i, content=part)
            formatted_thread.append(formatted)

        # Join with double newlines
        full_content = '\n\n'.join(formatted_thread)

        return {
            "content": full_content,
            "format": "thread",
            "parts": processed_parts,
            "warnings": warnings,
            "was_trimmed": was_trimmed,
            "thread_length": len(processed_parts)
        }

    def smart_trim(self, content: str, max_length: int) -> str:
        """
        Intelligently trim content preserving meaning

        Strategy:
        1. Try removing trailing rhetorical questions first
        2. Then trim from end sentence by sentence
        3. Add "..." if truncated mid-sentence
        4. Never break in middle of word
        """
        if len(content) <= max_length:
            return content

        # Strategy 1: Remove trailing question if present
        question_pattern = r'\s+[А-Яа-яA-Za-z\s,]+\?$'
        match = re.search(question_pattern, content)
        if match and len(content) - len(match.group(0)) <= max_length:
            trimmed = content[:match.start()].rstrip()
            if len(trimmed) <= max_length:
                logger.info("📐 Trimmed by removing trailing question")
                return trimmed + "."

        # Strategy 2: Trim sentence by sentence from end
        sentences = re.split(r'([.!?]\s+)', content)
        reconstructed = ""

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            punct = sentences[i+1] if i+1 < len(sentences) else ""

            if len(reconstructed + sentence + punct) <= max_length:
                reconstructed += sentence + punct
            else:
                # Can't fit this sentence
                break

        if reconstructed:
            logger.info("📐 Trimmed by removing sentences from end")
            return reconstructed.rstrip()

        # Strategy 3: Hard trim with "..." (last resort)
        # Find last complete word that fits
        target_length = max_length - 3  # Reserve for "..."
        trimmed = content[:target_length]

        # Find last space
        last_space = trimmed.rfind(' ')
        if last_space > 0:
            trimmed = trimmed[:last_space]

        logger.info("📐 Hard trimmed with ellipsis")
        return trimmed.rstrip() + "..."

    def validate_length(
        self,
        content: str,
        platform: str,
        format_type: str = "single"
    ) -> Dict[str, Any]:
        """
        Validate if content fits platform constraints

        Returns:
            {
                "valid": bool,
                "current_length": int,
                "max_length": int,
                "overflow": int,  # How many chars over (0 if valid)
                "recommendation": str
            }
        """
        if platform not in self.platform_configs:
            return {
                "valid": True,
                "current_length": len(content),
                "max_length": None,
                "overflow": 0,
                "recommendation": f"Unknown platform '{platform}'"
            }

        platform_config = self.platform_configs[platform]
        format_config = platform_config['formats'].get(format_type, platform_config['formats']['single'])

        max_length = format_config.get('max_chars', 500)
        current_length = len(content)
        overflow = max(0, current_length - max_length)

        return {
            "valid": current_length <= max_length,
            "current_length": current_length,
            "max_length": max_length,
            "overflow": overflow,
            "recommendation": f"Trim {overflow} characters" if overflow > 0 else "Length OK"
        }

    def _default_process(self, content: str) -> Dict[str, Any]:
        """Fallback processing for unknown platforms"""
        return {
            "content": content,
            "format": "single",
            "parts": [content],
            "warnings": ["Unknown platform - no processing applied"],
            "metadata": {
                "original_length": len(content),
                "final_length": len(content),
                "was_trimmed": False,
                "platform": "unknown",
                "format_type": "single"
            }
        }

    def get_platform_info(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get configuration info for a platform"""
        return self.platform_configs.get(platform)

    def list_supported_platforms(self) -> List[str]:
        """Get list of supported platforms"""
        return list(self.platform_configs.keys())
