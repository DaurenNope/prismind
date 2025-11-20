from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

import json

from .schemas import PersonaContext

PERSONA_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config" / "personas"


class PersonaManager:
    """
    Loads persona definitions from `config/personas` and exposes them as
    `PersonaContext` instances.

    This consolidates the scattered persona-loading logic currently duplicated
    across the legacy rewriter, scheduler, and Persona Studio endpoints.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, PersonaContext] = {}

    def get(self, persona_key: str) -> PersonaContext:
        if persona_key not in self._cache:
            self._cache[persona_key] = self._load_persona(persona_key)
        return self._cache[persona_key]

    @staticmethod
    @lru_cache(maxsize=128)
    def _load_persona(persona_key: str) -> PersonaContext:
        config_path = PERSONA_CONFIG_DIR / f"{persona_key}.json"
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            data = {"key": persona_key}

        return PersonaContext(
            key=data.get("key", persona_key),
            name=data.get("name"),
            language=data.get("language", data.get("default_language", "english")),
            tone=data.get("tone"),
            platforms=data.get("platforms", []),
        )


