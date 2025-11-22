from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import json
import re


CONFIG_DIR = Path(__file__).resolve().parents[3] / "config" / "personas"
DEFAULT_FRAGMENT_LIMIT = 2


class VoiceFragmentLibrary:
    """
    Lightweight loader/selector for persona-specific voice fragments.

    Each persona can optionally provide a `{persona_key}_voice_fragments.json`
    file (see `config/personas/qronoya_voice_fragments.json`) containing a list
    of short authentic snippets plus metadata (topics, mood, notes, etc.).
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or CONFIG_DIR

    def select_fragments(
        self,
        persona_key: str,
        analysis_payload: Dict[str, Any],
        *,
        limit: int = DEFAULT_FRAGMENT_LIMIT,
    ) -> List[Dict[str, Any]]:
        fragments = self._load_fragments(persona_key)
        if not fragments:
            return []

        topic_terms = self._extract_topics(analysis_payload)
        raw_text = self._extract_text(analysis_payload)

        scored: List[tuple[float, Dict[str, Any]]] = []
        for fragment in fragments:
            score = self._score_fragment(fragment, topic_terms, raw_text)
            scored.append((score, fragment))

        scored.sort(key=lambda item: item[0], reverse=True)

        # Keep positive matches first; fall back to top fragments if no overlap.
        positives = [frag for score, frag in scored if score > 0][:limit]
        if positives:
            return positives
        return [frag for _, frag in scored[:limit]]

    def _extract_topics(self, analysis_payload: Dict[str, Any]) -> set[str]:
        topics = set()
        raw_topics = analysis_payload.get("topics") or []

        if isinstance(raw_topics, dict):
            raw_topics = [raw_topics]

        for topic in raw_topics:
            if isinstance(topic, str):
                topics.add(topic.lower())
            elif isinstance(topic, dict):
                name = topic.get("name") or topic.get("label")
                if name:
                    topics.add(name.lower())

        for key in ("category", "content_type", "rewrite_category"):
            value = analysis_payload.get(key)
            if isinstance(value, str):
                topics.add(value.lower())

        return topics

    def _extract_text(self, analysis_payload: Dict[str, Any]) -> str:
        chunks = []
        for field in ("human_draft", "content", "summary", "ai_summary"):
            value = analysis_payload.get(field)
            if isinstance(value, str):
                chunks.append(value.lower())
        return " ".join(chunks)

    def _score_fragment(
        self,
        fragment: Dict[str, Any],
        topic_terms: set[str],
        raw_text: str,
    ) -> float:
        fragment_topics = {
            topic.lower().replace("_", " ").strip()
            for topic in fragment.get("topics", [])
            if isinstance(topic, str)
        }

        score = float(len(fragment_topics & topic_terms))

        # Keyword boost: if fragment topics appear in the raw text, bump score.
        for topic in fragment_topics:
            keyword = re.escape(topic)
            if keyword and re.search(rf"\b{keyword}\b", raw_text):
                score += 0.5

        return score

    @lru_cache(maxsize=64)
    def _load_fragments(self, persona_key: str) -> List[Dict[str, Any]]:
        path = self.base_dir / f"{persona_key}_voice_fragments.json"
        if not path.exists():
            return []

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        fragments = payload.get("fragments")
        if isinstance(fragments, list):
            return [frag for frag in fragments if isinstance(frag, dict)]

        return []



