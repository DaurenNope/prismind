#!/usr/bin/env python3
"""
Observability API Routes
=======================

API endpoints for observability metrics, errors, and system health.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from src.utils.logging_config import get_logger
from src.utils.observability_hub import get_observability_hub

router = APIRouter(prefix="/api/observability", tags=["observability"])
logger = get_logger(__name__)


@router.get("/health")
async def get_observability_health(request: Request):
    """Get observability hub health report"""
    try:
        hub = get_observability_hub()
        health = hub.get_health_report()
        return health
    except Exception as e:
        logger.error(f"Error getting observability health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics(request: Request, summary: bool = False):
    """Get metrics summary or detailed metrics"""
    try:
        hub = get_observability_hub()

        if summary:
            return {
                "total_metrics": hub.metrics.get_total_count(),
                "summary": hub.metrics.get_summary(),
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "metrics": hub.metrics.get_all_metrics(),
            "summary": hub.metrics.get_summary(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/errors")
async def get_errors(request: Request, limit: int = 50):
    """Get recent errors"""
    try:
        hub = get_observability_hub()
        error_summary = hub.errors.get_error_summary()

        return {
            "summary": error_summary,
            "recent_errors": hub.errors.get_recent_errors(limit=limit),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces")
async def get_traces(request: Request, limit: int = 20):
    """Get recent traces"""
    try:
        hub = get_observability_hub()
        traces = hub.traces.get_recent_traces(limit=limit)

        return {
            "traces": traces,
            "total_traces": len(traces),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_observability(request: Request):
    """Reset observability hub (clear metrics and errors)"""
    try:
        hub = get_observability_hub()
        hub.reset()

        return {
            "success": True,
            "message": "Observability hub reset successfully",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error resetting observability: {e}")
        raise HTTPException(status_code=500, detail=str(e))
