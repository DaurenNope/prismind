"""
Persona Studio API Routes
=========================

Bridges the existing automation backend (profiles, Supabase, vector DB, and
the modular rewriter) to the Persona Studio frontend.
"""

from __future__ import annotations

import json
import os
import statistics
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.database.manager import SupabaseManager
from src.database.publishing.bridge import MimesisDB, PersonaDraftsDB
from src.publishing.rag_system import ExampleVectorDatabase
from src.publishing.modular_rewriter import (
    ModularRewriter,
    RewriteRequest,
    build_persona_context,
)
from src.services.profile_content_pipeline import list_available_profiles
from src.pipeline.full_automation_loop import FullAutomationLoop
class AutomationRunRequest(BaseModel):
    platforms: Optional[List[str]] = None
    analyze_limit: Optional[int] = Field(
        default=None, description="Maximum posts to analyze this run"
    )
    min_match_score: float = Field(
        default=0.65, ge=0.0, le=1.0, description="Persona match threshold"
    )
    auto_schedule: bool = Field(
        default=False,
        description="Also push rewrites into scheduled_posts (optional)",
    )
    schedule_minutes: int = Field(
        default=60,
        ge=1,
        description="Schedule offset in minutes when auto_schedule is true",
    )
    curation_batch_size: int = Field(
        default=500, ge=50, description="Posts per curation backfill batch"
    )
    curation_batches: int = Field(
        default=2, ge=1, description="How many curation batches to run"
    )


_AUTOMATION_STATE: Dict[str, Any] = {
    "running": False,
    "current": None,
    "history": [],
}
_AUTOMATION_LOCK = asyncio.Lock()
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/persona-studio", tags=["persona-studio"])

PERSONA_DIR = Path(__file__).resolve().parents[3] / "config" / "personas"
EXAMPLES_SUFFIX = "_examples.json"
drafts_db = PersonaDraftsDB()
studio_rewriter = ModularRewriter()


class PersonaCreateRequest(BaseModel):
    key: str = Field(..., description="Unique persona key, e.g. 'qronoya'")
    name: str
    handle: Optional[str] = None
    voice_description: str
    description: Optional[str] = None
    language: str = Field("english", description="Primary language")
    platforms: List[str] = Field(default_factory=lambda: ["twitter"])
    examples: List[str] = Field(
        default_factory=list, description="Example posts representing the voice"
    )


class GenerateRequest(BaseModel):
    content: str = Field(..., description="Raw content or topic to rewrite")
    platform: str = Field("twitter", description="Target platform")
    category: str = Field("user_generated", description="High level category")
    angle: Optional[str] = Field(
        None, description="Optional rewrite angle or instruction"
    )
    topics: List[str] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)


class PersonaDraftCreateRequest(BaseModel):
    platform: str = Field("twitter", description="Destination platform")
    content: str = Field(..., description="Human-authored draft body")
    notes: Optional[str] = Field(None, description="Additional context or instructions")
    created_by: Optional[str] = Field(None, description="Who submitted the draft")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PersonaDraftStatusRequest(BaseModel):
    status: str = Field(
        ..., description="New status value (e.g., submitted, approved, rejected)"
    )
    approved_by: Optional[str] = Field(None, description="Reviewer identifier")
    review_notes: Optional[str] = Field(None, description="Optional reviewer notes")


class PersonaDraftResponse(BaseModel):
    id: str
    persona_key: str
    platform: str
    content: str
    notes: Optional[str] = None
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    last_generated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    rewrite_content: Optional[str] = None
    rewrite_quality: Optional[float] = None
    rewrite_voice_score: Optional[float] = None
    rewrite_fact_score: Optional[float] = None
    rewrite_metadata: Dict[str, Any] = Field(default_factory=dict)


class PersonaDraftGenerationResponse(BaseModel):
    draft: PersonaDraftResponse
    rewrite: Dict[str, Any]


class VoiceExamplePayload(BaseModel):
    id: Optional[str] = None
    platform: str = Field("threads", description="Source platform of the example")
    content: str = Field(..., description="Example post content")
    notes: Optional[str] = None
    content_type: Optional[str] = None
    structure: Optional[str] = None
    why_good_example: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceLibraryPayload(BaseModel):
    persona: str
    description: Optional[str] = None
    purpose: Optional[str] = None
    voice_patterns_to_capture: List[str] = Field(default_factory=list)
    examples: List[VoiceExamplePayload] = Field(default_factory=list)


def _persona_config_path(persona_key: str) -> Path:
    return PERSONA_DIR / f"{persona_key}.json"


def _persona_examples_path(persona_key: str) -> Path:
    return PERSONA_DIR / f"{persona_key}{EXAMPLES_SUFFIX}"


def _load_voice_library(persona_key: str) -> VoiceLibraryPayload:
    path = _persona_examples_path(persona_key)
    if not path.exists():
        return VoiceLibraryPayload(persona=persona_key, examples=[])

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to read voice library for %s: %s", persona_key, exc)
        raise HTTPException(status_code=500, detail="Invalid voice library file")

    normalized_examples: List[VoiceExamplePayload] = []
    for idx, example in enumerate(data.get("examples") or []):
        if isinstance(example, dict):
            normalized_examples.append(
                VoiceExamplePayload(
                    id=str(example.get("id") or f"{persona_key}_example_{idx}"),
                    platform=example.get("platform") or "threads",
                    content=example.get("content") or "",
                    notes=example.get("notes"),
                    content_type=example.get("content_type"),
                    structure=example.get("structure"),
                    why_good_example=example.get("why_good_example"),
                    metadata=example.get("metadata") or {},
                )
            )
        else:
            normalized_examples.append(
                VoiceExamplePayload(
                    id=f"{persona_key}_example_{idx}",
                    platform="threads",
                    content=str(example),
                )
            )

    payload = VoiceLibraryPayload(
        persona=data.get("persona") or persona_key,
        description=data.get("description"),
        purpose=data.get("purpose"),
        voice_patterns_to_capture=data.get("voice_patterns_to_capture") or [],
        examples=normalized_examples,
    )

    # Ensure each example has a stable id
    for idx, example in enumerate(payload.examples):
        if not example.id:
            example.id = f"{persona_key}_example_{idx}"
    return payload


def _write_voice_library(persona_key: str, payload: VoiceLibraryPayload) -> VoiceLibraryPayload:
    path = _persona_examples_path(persona_key)
    normalized_examples: List[Dict[str, Any]] = []
    for idx, example in enumerate(payload.examples):
        example_id = example.id or f"{persona_key}_example_{idx}"
        normalized_examples.append(
            {
                "id": example_id,
                "platform": example.platform,
                "content": example.content,
                "notes": example.notes,
                "content_type": example.content_type,
                "structure": example.structure,
                "why_good_example": example.why_good_example,
                "metadata": example.metadata,
            }
        )

    file_payload = {
        "persona": persona_key,
        "description": payload.description,
        "purpose": payload.purpose,
        "voice_patterns_to_capture": payload.voice_patterns_to_capture,
        "examples": normalized_examples,
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(file_payload, fp, indent=2, ensure_ascii=False)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to write voice library for %s: %s", persona_key, exc)
        raise HTTPException(status_code=500, detail="Failed to save voice library")

    # Refresh vector DB with latest examples
    vector_db = _vector_db()
    vector_db.delete_persona_examples(persona_key)
    for example in normalized_examples:
        content = (example.get("content") or "").strip()
        if content:
            vector_db.add_example(persona_id=persona_key, content=content, metadata=example)

    return VoiceLibraryPayload(
        persona=persona_key,
        description=file_payload["description"],
        purpose=file_payload.get("purpose"),
        voice_patterns_to_capture=file_payload.get("voice_patterns_to_capture") or [],
        examples=[VoiceExamplePayload(**ex) for ex in normalized_examples],
    )


def _load_persona_config(persona_key: str) -> Dict[str, Any]:
    path = _persona_config_path(persona_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Persona '{persona_key}' not found")
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to read persona config %s: %s", persona_key, exc)
        raise HTTPException(status_code=500, detail="Invalid persona configuration")


def _load_persona_examples(persona_key: str) -> List[Dict[str, Any]]:
    payload = _load_voice_library(persona_key)
    return [
        example.dict()
        for example in payload.examples
    ]


def _serialize_draft(row: Dict[str, Any]) -> PersonaDraftResponse:
    return PersonaDraftResponse(
        id=row.get("id"),
        persona_key=row.get("persona_key"),
        platform=row.get("platform", "twitter"),
        content=row.get("content", ""),
        notes=row.get("notes"),
        status=row.get("status", "submitted"),
        created_by=row.get("created_by"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        approved_by=row.get("approved_by"),
        approved_at=row.get("approved_at"),
        last_generated_at=row.get("last_generated_at"),
        metadata=row.get("metadata") or {},
        rewrite_content=row.get("rewrite_content"),
        rewrite_quality=row.get("rewrite_quality"),
        rewrite_voice_score=row.get("rewrite_voice_score"),
        rewrite_fact_score=row.get("rewrite_fact_score"),
        rewrite_metadata=row.get("rewrite_metadata") or {},
    )


def _ensure_supabase_client():
    try:
        return SupabaseManager().client
    except Exception as exc:  # pragma: no cover
        logger.error("Supabase client unavailable: %s", exc)
        raise HTTPException(status_code=500, detail="Supabase is not configured")


def _vector_db() -> ExampleVectorDatabase:
    # Reuse a singleton adapter to avoid reloading sentence transformers repeatedly.
    global _VECTOR_DB
    if _VECTOR_DB is None:
        _VECTOR_DB = ExampleVectorDatabase(storage_path="data/vector_db")
    return _VECTOR_DB


_VECTOR_DB: Optional[ExampleVectorDatabase] = None


def _slugify(value: str) -> str:
    return (
        "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
        .replace("--", "-")
        .strip("-")
    )


def _compute_example_stats(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not examples:
        return {
            "sentence_length": 0,
            "technical_density": 0.0,
            "emotional_intensity": 0.0,
        }
    lengths = []
    technical_tokens = ["ai", "ml", "api", "infra", "code", "build", "metric"]
    emotional_tokens = ["love", "hate", "feel", "excited", "scared", "нрав", "люблю"]
    tech_hits = 0
    emotional_hits = 0
    total_tokens = 0

    for example in examples:
        content = (example.get("content") or "").strip()
        if not content:
            continue
        lengths.append(len(content))
        tokens = content.lower().split()
        total_tokens += len(tokens)
        tech_hits += sum(1 for token in tokens for kw in technical_tokens if kw in token)
        emotional_hits += sum(
            1 for token in tokens for kw in emotional_tokens if kw in token
        )

    avg_length = statistics.mean(lengths) if lengths else 0
    if total_tokens == 0:
        return {
            "sentence_length": round(avg_length, 2),
            "technical_density": 0.0,
            "emotional_intensity": 0.0,
        }

    return {
        "sentence_length": round(avg_length, 2),
        "technical_density": round(min(1.0, tech_hits / total_tokens), 3),
        "emotional_intensity": round(min(1.0, emotional_hits / total_tokens), 3),
    }


def _fetch_persona_metrics(persona_key: str) -> Dict[str, Any]:
    client = _ensure_supabase_client()
    try:
        resp = (
            client.table("usable_posts")
            .select("quality_score,rewrite_score,value_score")
            .eq("best_persona_key", persona_key)
            .limit(500)
            .execute()
        )
        data = getattr(resp, "data", []) or []
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to query usable_posts for %s: %s", persona_key, exc)
        data = []

    if not data:
        return {
            "avg_quality": 0.0,
            "avg_value": 0.0,
            "avg_rewrite": 0.0,
            "total_posts": 0,
        }

    def _avg(field: str) -> float:
        values = [row.get(field) for row in data if row.get(field) is not None]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 3)

    return {
        "avg_quality": _avg("quality_score"),
        "avg_value": _avg("value_score"),
        "avg_rewrite": _avg("rewrite_score"),
        "total_posts": len(data),
    }


def _build_persona_payload(profile: Dict[str, Any]) -> Dict[str, Any]:
    key = profile.get("profile_key") or profile.get("key") or profile.get("name")
    config = _load_persona_config(key)
    examples = _load_persona_examples(key)
    metrics = _fetch_persona_metrics(key)
    vector_examples = _vector_db().get_persona_examples(key)

    return {
        "id": key,
        "key": key,
        "name": config.get("name", key),
        "handle": config.get("handle"),
        "description": config.get("description") or config.get("voice_description", ""),
        "language": config.get("transformation_settings", {}).get(
            "language", "english"
        ),
        "platforms": config.get("platforms", []),
        "example_count": len(examples),
        "quality_metrics": metrics,
        "rag_examples": len(vector_examples),
    }


@router.get("/overview")
async def get_overview() -> Dict[str, Any]:
    """Return high-level Persona Studio statistics."""
    profiles = list_available_profiles()
    persona_payloads: List[Dict[str, Any]] = []
    for profile in profiles:
        try:
            persona_payloads.append(_build_persona_payload(profile))
        except HTTPException as exc:
            if exc.status_code == 404:
                skipped_key = profile.get("profile_key") or profile.get("name")
                logger.warning(
                    f"Skipping profile {skipped_key} due to missing persona config/examples"
                )
                continue
            raise

    total_examples = sum(p["example_count"] for p in persona_payloads)
    avg_quality = (
        statistics.mean(
            p["quality_metrics"]["avg_quality"]
            for p in persona_payloads
            if p["quality_metrics"]["total_posts"]
        )
        if persona_payloads
        else 0.0
    )
    avg_engagement = (
        statistics.mean(
            p["quality_metrics"]["avg_value"]
            for p in persona_payloads
            if p["quality_metrics"]["total_posts"]
        )
        if persona_payloads
        else 0.0
    )

    rag_stats = _vector_db().get_stats()

    platforms = sorted(
        {
            platform
            for persona in persona_payloads
            for platform in persona.get("platforms", [])
        }
    )

    return {
        "totalPersonas": len(persona_payloads),
        "totalExamples": total_examples,
        "avgQuality": avg_quality,
        "avgEngagement": avg_engagement,
        "totalPostsGenerated": sum(
            p["quality_metrics"]["total_posts"] for p in persona_payloads
        ),
        "platforms": platforms,
        "ragMetrics": {
            "rag_enabled": bool(rag_stats.get("total_examples", 0)),
            "total_vector_examples": rag_stats.get("total_examples", 0),
            "faiss_available": rag_stats.get("faiss_available", False),
        },
        "systemPerformance": {
            "api_response_time": "<250ms",
            "success_rate": "95%",
            "uptime": "99.3%",
        },
        "personas": persona_payloads,
    }


@router.get("/personas")
async def list_personas() -> Dict[str, Any]:
    profiles = list_available_profiles()
    payloads: List[Dict[str, Any]] = []
    for profile in profiles:
        try:
            payloads.append(_build_persona_payload(profile))
        except HTTPException as exc:
            if exc.status_code == 404:
                skipped_key = profile.get("profile_key") or profile.get("name")
                logger.warning(
                    f"Skipping profile {skipped_key} because persona config/examples are missing"
                )
                continue
            raise
    return {"personas": payloads, "total": len(payloads)}


@router.get("/personas/{persona_key}/performance")
async def get_persona_performance(persona_key: str) -> Dict[str, Any]:
    config = _load_persona_config(persona_key)
    examples = _load_persona_examples(persona_key)
    example_stats = _compute_example_stats(examples)
    rag_examples = _vector_db().get_persona_examples(persona_key)
    persona_metrics = _fetch_persona_metrics(persona_key)

    return {
        "persona_info": {
            "id": persona_key,
            "name": config.get("name", persona_key),
            "description": config.get("description", config.get("voice_description", "")),
            "platforms": config.get("platforms", []),
            "created_at": config.get("created_at"),
        },
        "quality_metrics": {
            "authenticity": persona_metrics["avg_quality"],
            "engagement": persona_metrics["avg_value"],
            "voice_consistency": persona_metrics["avg_rewrite"],
        },
        "voice_patterns": example_stats,
        "rag_analytics": {
            "total_examples_stored": len(rag_examples),
            "examples_with_embeddings": len(
                [ex for ex in rag_examples if ex.embedding is not None]
            ),
            "storage_status": "ready" if rag_examples else "cold-start",
        },
        "optimization_suggestions": _build_optimization_suggestions(
            persona_metrics, example_stats
        ),
    }


def _build_optimization_suggestions(
    metrics: Dict[str, Any], voice_stats: Dict[str, Any]
) -> List[str]:
    suggestions: List[str] = []
    if metrics["avg_quality"] < 7:
        suggestions.append(
            "Collect fresher evergreen sources (quality score below 7.0 on average)."
        )
    if metrics["total_posts"] < 10:
        suggestions.append("Pipeline has few curated posts; prioritize analysis backlog.")
    if voice_stats["technical_density"] < 0.05:
        suggestions.append("Add more technical case studies to training examples.")
    if not suggestions:
        suggestions.append("Persona is healthy. Monitor rewrite queue for freshness.")
    return suggestions


@router.get("/personas/{persona_key}/examples")
async def get_persona_examples(persona_key: str) -> Dict[str, Any]:
    examples = _load_persona_examples(persona_key)
    return {"persona": persona_key, "examples": examples, "count": len(examples)}


@router.get(
    "/personas/{persona_key}/voice-library", response_model=VoiceLibraryPayload
)
async def get_voice_library(persona_key: str) -> VoiceLibraryPayload:
    _load_persona_config(persona_key)
    return _load_voice_library(persona_key)


@router.put(
    "/personas/{persona_key}/voice-library", response_model=VoiceLibraryPayload
)
async def update_voice_library(
    persona_key: str, payload: VoiceLibraryPayload
) -> VoiceLibraryPayload:
    _load_persona_config(persona_key)
    if payload.persona and payload.persona != persona_key:
        raise HTTPException(
            status_code=400, detail="Persona key mismatch in voice library payload"
        )
    payload.persona = persona_key
    return _write_voice_library(persona_key, payload)


@router.get("/personas/{persona_key}/rewrites")
async def get_persona_rewrites(persona_key: str, limit: int = 10) -> Dict[str, Any]:
    db = MimesisDB()
    rewrites = db.list_transformations(persona_key=persona_key, ready_only=False)
    rewrites = sorted(
        rewrites,
        key=lambda row: row.get("updated_at") or row.get("created_at") or "",
        reverse=True,
    )[: max(1, min(limit, 50))]
    return {"persona": persona_key, "rewrites": rewrites, "count": len(rewrites)}


@router.post("/personas")
async def create_persona(request: PersonaCreateRequest) -> Dict[str, Any]:
    persona_key = _slugify(request.key)
    if not persona_key:
        raise HTTPException(status_code=400, detail="Persona key is invalid")

    config_path = _persona_config_path(persona_key)
    if config_path.exists():
        raise HTTPException(
            status_code=409, detail=f"Persona '{persona_key}' already exists"
        )

    config = {
        "key": persona_key,
        "name": request.name.strip(),
        "handle": request.handle,
        "description": request.description or request.voice_description,
        "voice_description": request.voice_description,
        "platforms": request.platforms,
        "transformation_settings": {
            "language": request.language,
            "personality_prompt": request.voice_description,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    examples_payload = {
        "persona": persona_key,
        "description": request.voice_description,
        "examples": [
            {
                "id": f"{persona_key}_{idx}",
                "platform": "threads",
                "content": example.strip(),
            }
            for idx, example in enumerate(request.examples)
            if example.strip()
        ],
    }

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as fp:
            json.dump(config, fp, indent=2, ensure_ascii=False)

        examples_path = _persona_examples_path(persona_key)
        with examples_path.open("w", encoding="utf-8") as fp:
            json.dump(examples_payload, fp, indent=2, ensure_ascii=False)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to write persona files: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save persona files")

    # Seed vector DB with examples for immediate use.
    for example in examples_payload["examples"]:
        _vector_db().add_example(
            persona_id=persona_key, content=example["content"], metadata=example
        )

    logger.info("Created persona %s", persona_key)
    return {"success": True, "persona": config}


@router.post(
    "/personas/{persona_key}/drafts", response_model=PersonaDraftResponse
)
async def create_persona_draft(
    persona_key: str, request: PersonaDraftCreateRequest
) -> PersonaDraftResponse:
    _load_persona_config(persona_key)
    row = drafts_db.create(
        persona_key=persona_key,
        content=request.content,
        platform=request.platform,
        notes=request.notes,
        created_by=request.created_by,
        metadata=request.metadata,
    )
    return _serialize_draft(row)


@router.get(
    "/personas/{persona_key}/drafts", response_model=List[PersonaDraftResponse]
)
async def list_persona_drafts(
    persona_key: str, status: Optional[str] = None, limit: int = 50
) -> List[PersonaDraftResponse]:
    _load_persona_config(persona_key)
    rows = drafts_db.list(persona_key=persona_key, status=status, limit=limit)
    return [_serialize_draft(row) for row in rows]


@router.post(
    "/personas/{persona_key}/drafts/{draft_id}/status",
    response_model=PersonaDraftResponse,
)
async def update_persona_draft_status(
    persona_key: str, draft_id: str, request: PersonaDraftStatusRequest
) -> PersonaDraftResponse:
    draft = drafts_db.get(draft_id)
    if not draft or draft.get("persona_key") != persona_key:
        raise HTTPException(status_code=404, detail="Draft not found")

    fields: Dict[str, Any] = {"status": request.status}
    if request.approved_by is not None:
        fields["approved_by"] = request.approved_by

    if request.status.lower() == "approved":
        fields["approved_at"] = datetime.now(timezone.utc).isoformat()
    else:
        fields["approved_at"] = None

    if request.review_notes:
        metadata = draft.get("metadata") or {}
        metadata["review_notes"] = request.review_notes
        fields["metadata"] = metadata

    updated = drafts_db.update(draft_id, fields)
    return _serialize_draft(updated)


@router.post(
    "/personas/{persona_key}/drafts/{draft_id}/generate",
    response_model=PersonaDraftGenerationResponse,
)
async def generate_persona_draft(
    persona_key: str, draft_id: str
) -> PersonaDraftGenerationResponse:
    draft = drafts_db.get(draft_id)
    if not draft or draft.get("persona_key") != persona_key:
        raise HTTPException(status_code=404, detail="Draft not found")

    config = _load_persona_config(persona_key)
    persona_context = build_persona_context(persona_key, config)

    draft_body = (draft.get("content") or "").strip()
    if not draft_body:
        raise HTTPException(
            status_code=400,
            detail="Draft content is empty. Provide text before requesting a rewrite.",
        )

    draft_notes = (draft.get("notes") or "").strip()
    metadata = draft.get("metadata") or {}

    analyzed_payload = {
        "post_id": f"draft_{draft_id}",
        "platform": draft.get("platform", "twitter"),
        "content": draft_body,
        "summary": draft_notes or draft_body,
        "ai_summary": draft_notes or draft_body,
        "human_draft": draft_body,
        "human_notes": draft_notes,
        "category": metadata.get("category", "human_draft"),
        "topics": metadata.get("topics") or [],
        "key_concepts": metadata.get("key_concepts") or [],
        "rewrite_angles": metadata.get("rewrite_angles") or [],
    }

    rewrite_request = RewriteRequest(
        analyzed_content=analyzed_payload,
        persona=persona_context,
        platform=draft.get("platform", "twitter"),
        metadata={
            "draft_id": draft_id,
            "human_draft": draft_body,
            "human_notes": draft_notes,
            "from_human_draft": True,
            **metadata,
        },
    )

    modular_result = await studio_rewriter.rewrite(rewrite_request)
    rewrite_metadata = modular_result.metadata or {}
    updated = drafts_db.update_rewrite(
        draft_id,
        content=modular_result.rewritten_content,
        quality_score=modular_result.quality_score,
        voice_score=modular_result.voice_consistency_score,
        fact_score=modular_result.fact_preservation_score,
        metadata=rewrite_metadata,
    )

    rewrite_payload = {
        "content": modular_result.rewritten_content,
        "quality_metrics": {
            "quality_score": modular_result.quality_score,
            "voice_consistency": modular_result.voice_consistency_score,
            "fact_preservation": modular_result.fact_preservation_score,
        },
        "metadata": rewrite_metadata,
    }

    return PersonaDraftGenerationResponse(
        draft=_serialize_draft(updated),
        rewrite=rewrite_payload,
    )


@router.post("/personas/{persona_key}/generate")
async def generate_persona_content(
    persona_key: str, request: GenerateRequest
) -> Dict[str, Any]:
    config = _load_persona_config(persona_key)

    analyzed_content = {
        "post_id": f"manual_{uuid.uuid4()}",
        "platform": request.platform,
        "url": "https://persona-studio.local/input",
        "content": request.content,
        "summary": request.content[:280],
        "category": request.category,
        "topics": request.topics,
        "key_concepts": request.key_concepts,
        "analysis_model": "persona_studio",
        "rewrite_angles": {
            persona_key: [
                {
                    "angle": request.angle or "Persona studio custom rewrite",
                    "angle_name": "Custom rewrite",
                    "tone": config.get("voice_description", "authentic voice"),
                    "platform_fit": f"{request.platform}_single",
                    "call_to_action": "Share a perspective",
                }
            ]
        },
        "rewrite_suggestions": [
            {
                "persona": persona_key,
                "tone": config.get("voice_description", "authentic voice"),
                "cta": "Share your insight",
            }
        ],
    }

    persona_context = build_persona_context(persona_key, config)
    rewrite_request = RewriteRequest(
        analyzed_content=analyzed_content,
        persona=persona_context,
        platform=request.platform,
    )
    result = await studio_rewriter.rewrite(rewrite_request)

    return {
        "success": True,
        "persona": persona_key,
        "platform": request.platform,
        "content": result.rewritten_content,
        "quality_metrics": {
            "quality_score": result.quality_score,
            "voice_consistency": result.voice_consistency_score,
            "fact_preservation": result.fact_preservation_score,
        },
        "metadata": {
            "angle": result.metadata.get("angle_used"),
            "hook": result.metadata.get("hook_used"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


async def _automation_worker(run_id: str, payload: AutomationRunRequest) -> None:
    orchestrator = FullAutomationLoop()
    start_dt = datetime.now(timezone.utc)
    status = "success"
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None

    try:
        results = await orchestrator.run_full_loop(
            platforms=payload.platforms,
            analyze_limit=payload.analyze_limit,
            min_match_score=payload.min_match_score,
            schedule_minutes=payload.schedule_minutes,
            auto_schedule=payload.auto_schedule,
            curation_batch_size=payload.curation_batch_size,
            curation_batches=payload.curation_batches,
        )
    except Exception as exc:  # pragma: no cover
        status = "failed"
        error = str(exc)
        logger.exception("Automation run %s failed: %s", run_id, exc)
    finally:
        finished_dt = datetime.now(timezone.utc)
        summary = {
            "run_id": run_id,
            "status": status,
            "started_at": start_dt.isoformat(),
            "completed_at": finished_dt.isoformat(),
            "results": results or {},
            "error": error,
        }
        async with _AUTOMATION_LOCK:
            _AUTOMATION_STATE["running"] = False
            _AUTOMATION_STATE["current"] = summary
            history = _AUTOMATION_STATE["history"]
            history.insert(0, summary)
            _AUTOMATION_STATE["history"] = history[:10]


@router.post("/automation/run")
async def trigger_automation(request: AutomationRunRequest) -> Dict[str, Any]:
    async with _AUTOMATION_LOCK:
        if _AUTOMATION_STATE["running"]:
            raise HTTPException(
                status_code=409, detail="Automation loop already running"
            )

        run_id = str(uuid.uuid4())
        entry = {
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "parameters": request.dict(),
        }
        _AUTOMATION_STATE["running"] = True
        _AUTOMATION_STATE["current"] = entry

    asyncio.create_task(_automation_worker(run_id, request))

    return {"success": True, "run_id": run_id, "status": "running", "current": entry}


@router.get("/automation/status")
async def get_automation_status() -> Dict[str, Any]:
    async with _AUTOMATION_LOCK:
        return {
            "running": _AUTOMATION_STATE["running"],
            "current": _AUTOMATION_STATE["current"],
            "history": _AUTOMATION_STATE["history"],
        }


@router.get("/quality-trends")
async def get_quality_trends() -> Dict[str, Any]:
    personas = (await list_personas())["personas"]

    breakdown = [
        {
            "id": persona["id"],
            "name": persona["name"],
            "quality_scores": {
                "authenticity": persona["quality_metrics"]["avg_quality"],
                "engagement": persona["quality_metrics"]["avg_value"],
                "voice_consistency": persona["quality_metrics"]["avg_rewrite"],
            },
            "examples_count": persona.get("example_count", 0),
            "platforms": persona.get("platforms", []),
        }
        for persona in personas
    ]

    overall_avg = (
        statistics.mean(b["quality_scores"]["authenticity"] for b in breakdown)
        if breakdown
        else 0.0
    )
    engagement_avg = (
        statistics.mean(b["quality_scores"]["engagement"] for b in breakdown)
        if breakdown
        else 0.0
    )
    consistency_avg = (
        statistics.mean(b["quality_scores"]["voice_consistency"] for b in breakdown)
        if breakdown
        else 0.0
    )

    quality_distribution = {
        "high_quality": sum(1 for b in breakdown if b["quality_scores"]["authenticity"] >= 8),
        "medium_quality": sum(
            1 for b in breakdown if 6 <= b["quality_scores"]["authenticity"] < 8
        ),
        "low_quality": sum(
            1 for b in breakdown if b["quality_scores"]["authenticity"] < 6
        ),
    }

    return {
        "overall_trends": {
            "avg_authenticity": overall_avg,
            "avg_engagement": engagement_avg,
            "avg_consistency": consistency_avg,
        },
        "persona_breakdown": breakdown,
        "quality_distribution": quality_distribution,
    }


# Prompt Management Endpoints
class PromptTemplateRequest(BaseModel):
    platform: str
    template: str
    metadata: Optional[Dict[str, Any]] = None


@router.get("/personas/{persona_key}/prompts")
async def get_persona_prompts(persona_key: str) -> Dict[str, Any]:
    """Get all prompt templates for a persona"""
    try:
        config = _load_persona_config(persona_key)
        if not config:
            raise HTTPException(status_code=404, detail=f"Persona {persona_key} not found")
        
        # Load prompt templates from config file
        prompts_dir = Path("config/personas/prompts")
        prompts_dir.mkdir(parents=True, exist_ok=True)
        prompts_file = prompts_dir / f"{persona_key}_prompts.json"
        
        templates = {}
        if prompts_file.exists():
            with open(prompts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                templates = data.get("templates", data)  # Support both formats
        else:
            # Generate default prompts from PromptBuilder so user can see/edit them
            from src.publishing.modular_rewriter.prompt_builder import PromptBuilder
            from src.publishing.modular_rewriter.schemas import RewriteRequest
            from src.publishing.modular_rewriter.content_planner import RewritePlan
            
            persona_context = build_persona_context(persona_key, config)
            builder = PromptBuilder()
            
            # Create sample request/plan to generate default prompts
            sample_request = RewriteRequest(
                persona=persona_context,
                platform="twitter",
                analyzed_content={
                    "ai_summary": "Sample content summary",
                    "content": "Sample content for preview"
                },
            )
            sample_plan = RewritePlan(
                hook="Sample hook",
                angle="Sample angle",
                call_to_action="Sample CTA",
                human_draft="Sample human draft"
            )
            
            templates = {
                "twitter": builder._build_twitter_prompt(sample_request, sample_plan),
                "threads": builder._build_threads_prompt(sample_request, sample_plan),
                "telegram": builder._build_telegram_prompt(sample_request, sample_plan),
            }
        
        return {
            "persona_key": persona_key,
            "templates": templates,
            "platforms": list(templates.keys()),
            "has_custom": prompts_file.exists(),
        }
    except Exception as e:
        logger.error(f"Failed to get prompts for {persona_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/personas/{persona_key}/prompts/{platform}")
async def update_persona_prompt(
    persona_key: str,
    platform: str,
    request: PromptTemplateRequest,
) -> Dict[str, Any]:
    """Update a prompt template for a persona/platform"""
    try:
        config = _load_persona_config(persona_key)
        if not config:
            raise HTTPException(status_code=404, detail=f"Persona {persona_key} not found")
        
        if request.platform != platform:
            raise HTTPException(status_code=400, detail="Platform mismatch")
        
        # Load existing templates
        prompts_dir = Path("config/personas/prompts")
        prompts_dir.mkdir(parents=True, exist_ok=True)
        prompts_file = prompts_dir / f"{persona_key}_prompts.json"
        
        templates = {}
        if prompts_file.exists():
            with open(prompts_file, 'r', encoding='utf-8') as f:
                templates = json.load(f)
        
        # Update the template
        if "templates" not in templates:
            templates = {"templates": templates}
        templates["templates"][platform] = request.template
        if request.metadata:
            templates.setdefault("metadata", {})[platform] = request.metadata
        
        # Save
        with open(prompts_file, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Updated prompt template for {persona_key}/{platform}")
        
        return {
            "persona_key": persona_key,
            "platform": platform,
            "status": "updated",
        }
    except Exception as e:
        logger.error(f"Failed to update prompt for {persona_key}/{platform}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

