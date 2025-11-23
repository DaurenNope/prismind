from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import PersonaContext

logger = logging.getLogger(__name__)

PERSONA_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config" / "personas"


class PersonaManager:
    """
    Loads persona definitions from `config/personas` and exposes them as
    `PersonaContext` instances with complete context (examples, voice fragments, expertise).

    Features:
    - Lazy loading with caching
    - Full context loading (examples, voice fragments, expertise)
    - Performance optimized (< 100ms per persona load)
    - Backward compatible
    """

    def __init__(self) -> None:
        self._cache: Dict[str, PersonaContext] = {}
        self._examples_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._fragments_cache: Dict[str, List[Dict[str, Any]]] = {}

    def get(self, persona_key: str) -> PersonaContext:
        """Get persona context with caching."""
        if persona_key not in self._cache:
            self._cache[persona_key] = self._load_persona(persona_key)
        return self._cache[persona_key]

    def get_examples(
        self, persona_key: str, content_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get examples for a persona, optionally filtered by content type.
        
        Args:
            persona_key: Persona identifier
            content_type: Optional filter (e.g., "product_launch", "tech_analysis")
        
        Returns:
            List of example dictionaries
        """
        if persona_key not in self._examples_cache:
            self._examples_cache[persona_key] = self._load_examples(persona_key)
        
        examples = self._examples_cache[persona_key]
        
        if content_type:
            return [
                ex for ex in examples
                if ex.get("content_type", "").lower() == content_type.lower()
            ]
        
        return examples

    def get_voice_fragments(
        self, persona_key: str, topics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get voice fragments for a persona, optionally filtered by topics.
        
        Args:
            persona_key: Persona identifier
            topics: Optional list of topics to match against fragment topics
        
        Returns:
            List of voice fragment dictionaries
        """
        if persona_key not in self._fragments_cache:
            self._fragments_cache[persona_key] = self._load_voice_fragments(persona_key)
        
        fragments = self._fragments_cache[persona_key]
        
        if topics:
            topic_set = {t.lower() for t in topics}
            return [
                frag for frag in fragments
                if topic_set.intersection({t.lower() for t in frag.get("topics", [])})
            ]
        
        return fragments

    def get_expertise(self, persona_key: str) -> List[str]:
        """Get expertise areas for a persona."""
        persona = self.get(persona_key)
        return persona.expertise

    @staticmethod
    @lru_cache(maxsize=128)
    def _load_persona(persona_key: str) -> PersonaContext:
        """Load persona with all available context files."""
        import time
        start = time.time()
        
        config_path = PERSONA_CONFIG_DIR / f"{persona_key}.json"
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            logger.warning(f"Persona config not found: {config_path}")
            data = {"key": persona_key}

        # Load examples file (lazy, cached separately)
        examples = PersonaManager._load_examples(persona_key)
        
        # Load voice fragments file (lazy, cached separately)
        voice_fragments = PersonaManager._load_voice_fragments(persona_key)

        elapsed = (time.time() - start) * 1000
        if elapsed > 100:
            logger.warning(f"PersonaManager._load_persona took {elapsed:.2f}ms (target: <100ms)")

        return PersonaContext(
            key=data.get("key", persona_key),
            name=data.get("name"),
            language=data.get("language", data.get("default_language", "english")),
            tone=data.get("tone"),
            platforms=data.get("platforms", []),
            voice_description=data.get("voice_description"),
            expertise=data.get("expertise", []),
            examples=examples,
            voice_fragments=voice_fragments,
        )

    @staticmethod
    @lru_cache(maxsize=128)
    def _load_examples(persona_key: str) -> List[Dict[str, Any]]:
        """Load examples from {persona_key}_examples.json file."""
        examples_path = PERSONA_CONFIG_DIR / f"{persona_key}_examples.json"
        if not examples_path.exists():
            logger.debug(f"Examples file not found for {persona_key}: {examples_path}")
            return []
        
        try:
            data = json.loads(examples_path.read_text(encoding="utf-8"))
            # Handle both array format and object with "examples" key
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "examples" in data:
                return data["examples"]
            else:
                logger.warning(f"Unexpected format in {examples_path}")
                return []
        except Exception as e:
            logger.warning(f"Failed to load examples for {persona_key}: {e}")
            return []

    @staticmethod
    @lru_cache(maxsize=128)
    def _load_voice_fragments(persona_key: str) -> List[Dict[str, Any]]:
        """Load voice fragments from {persona_key}_voice_fragments.json file."""
        fragments_path = PERSONA_CONFIG_DIR / f"{persona_key}_voice_fragments.json"
        if not fragments_path.exists():
            logger.debug(f"Voice fragments file not found for {persona_key}: {fragments_path}")
            return []
        
        try:
            data = json.loads(fragments_path.read_text(encoding="utf-8"))
            # Handle both array format and object with "fragments" key
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "fragments" in data:
                return data["fragments"]
            elif isinstance(data, dict):
                # If it's a dict with fragment objects, convert to list
                return list(data.values()) if data else []
            else:
                logger.warning(f"Unexpected format in {fragments_path}")
                return []
        except Exception as e:
            logger.warning(f"Failed to load voice fragments for {persona_key}: {e}")
            return []
