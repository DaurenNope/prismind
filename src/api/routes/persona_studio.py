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
from src.database.publishing.bridge import MimesisDB
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


def _persona_config_path(persona_key: str) -> Path:
    return PERSONA_DIR / f"{persona_key}.json"


def _persona_examples_path(persona_key: str) -> Path:
    return PERSONA_DIR / f"{persona_key}{EXAMPLES_SUFFIX}"


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
    path = _persona_examples_path(persona_key)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        examples = payload.get("examples") or []
        # Normalize to dicts with id/content
        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(examples):
            if isinstance(item, str):
                normalized.append(
                    {
                        "id": f"{persona_key}_{idx}",
                        "content": item,
                        "platform": "threads",
                    }
                )
            elif isinstance(item, dict):
                normalized.append(item)
        return normalized
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to read examples for %s: %s", persona_key, exc)
        raise HTTPException(status_code=500, detail="Invalid persona examples file")


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


@router.post("/personas/{persona_key}/generate")
async def generate_persona_content(
    persona_key: str, request: GenerateRequest
) -> Dict[str, Any]:
    config = _load_persona_config(persona_key)
    rewriter = ModularRewriter()

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
    result = await rewriter.rewrite(rewrite_request)

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

