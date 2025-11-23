from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

import requests

from src.database.manager import SupabaseManager


class SimpleTransformer:
    """
    Minimal persona transformer.

    DEPRECATED: This is a fallback transformer. Consider using ModularRewriter
    for better quality and consistency.

    If Ollama/QWEN endpoint is configured, uses it; otherwise returns a simple
    templated rewrite based on the source content/title.
    """

    def __init__(
        self, qwen_url: Optional[str] = None, model: Optional[str] = None
    ) -> None:
        self.qwen_url = qwen_url or os.getenv("QWEN_API_URL")
        self.model = model or os.getenv("ENGLISH_MODEL", "qwen2.5:7b")

    def _ollama_generate(self, prompt: str) -> Optional[str]:
        if not self.qwen_url:
            return None
        try:
            resp = requests.post(
                self.qwen_url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            # Ollama returns { response: "..." }
            return (data.get("response") or "").strip() or None
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def transform(self, persona_key: str, source: Dict[str, object]) -> str:
        title = str(source.get("title") or "").strip()
        content = str(source.get("content") or "").strip()
        base = title or content[:280]
        base = base.replace("\n", " ")

        prompt = (
            f"Persona: {persona_key}.\n"
            f"Rewrite the following into a concise social post in the persona voice,"
            f" under 240 characters, no hashtags unless critical, no emojis unless additive.\n"
            f"Text: {base}\n"
            f"Output only the rewritten post."
        )

        generated = self._ollama_generate(prompt)
        if generated:
            return generated

        # Fallback deterministic template
        snippet = (title or content).strip().replace("\n", " ")
        snippet = snippet[:220]
        return f"[{persona_key}] {snippet}"


class PersonaGenerator:
    """Generate and schedule persona posts from existing posts."""

    def __init__(
        self,
        sb: Optional[SupabaseManager] = None,
        transformer: Optional[SimpleTransformer] = None,
    ) -> None:
        self.sb = sb or SupabaseManager.from_env()
        self.transformer = transformer or SimpleTransformer()

    def generate_and_schedule(
        self,
        persona_key: str,
        platform: str,
        sources: Iterable[Dict[str, object]],
        schedule_in_minutes: int = 1,
    ) -> List[Dict[str, object]]:
        scheduled: List[Dict[str, object]] = []
        when = datetime.now(timezone.utc) + timedelta(minutes=schedule_in_minutes)

        content_type_map = {
            "twitter": "single_tweet",
            "threads": "single_tweet",
            "telegram": "telegram_message",
        }
        for src in sources:
            text = self.transformer.transform(persona_key, src)
            row = {
                "personality_key": persona_key,  # Support both schema variants
                "persona_key": persona_key,
                "platform": platform,
                "content": text,
                "content_type": content_type_map.get(platform, "single_tweet"),
                "scheduled_time": when.isoformat(),  # scheduled_posts table uses scheduled_time
                "status": "pending",  # Database uses 'pending', not 'scheduled'
            }
            # Use DatabaseAgent (delegates to StorageFacade)
            from src.infrastructure.database.database_agent import get_database_agent

            db_agent = get_database_agent()
            if db_agent.save_scheduled_post(row):
                # Get the inserted record if needed
                try:
                    result = (
                        self.sb.client.table("scheduled_posts")
                        .select("*")
                        .eq("content", row.get("content"))
                        .limit(1)
                        .execute()
                    )
                    if result.data:
                        scheduled.append(result.data[0])
                except Exception as e:
                    logger.error(f"Error: {e}")
                    scheduled.append(row)  # Fallback to row data
        return scheduled

    def generate_transformations(
        self,
        persona_key: str,
        sources: Iterable[Dict[str, object]],
    ) -> List[Dict[str, object]]:
        """Write rewrites into persona_transformations for later approval."""
        created: List[Dict[str, object]] = []
        for src in sources:
            text = self.transformer.transform(persona_key, src)
            row = {
                "persona_key": persona_key,
                "source_post_id": str(src.get("post_id") or src.get("id") or ""),
                "platform": str(src.get("platform") or "twitter"),
                "content": text,
                "ready_for_posting": False,
            }
            # Use DatabaseAgent (delegates to StorageFacade)
            from src.infrastructure.database.database_agent import get_database_agent

            db_agent = get_database_agent()
            if db_agent.save_transformation(row):
                # Get the inserted record if needed
                try:
                    result = (
                        self.sb.client.table("persona_transformations")
                        .select("*")
                        .eq("content", row.get("content"))
                        .eq("persona_key", persona_key)
                        .limit(1)
                        .execute()
                    )
                    if result.data:
                        created.append(result.data[0])
                except Exception as e:
                    logger.error(f"Error: {e}")
                    created.append(row)  # Fallback to row data
        return created
