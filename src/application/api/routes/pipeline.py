"""
Pipeline Status API Routes
Handles real-time pipeline status and metrics
"""
import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.shared.utils.logging_config import get_logger
from src.services.pipeline_status import PipelineStatusService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/status")
async def get_pipeline_status():
    """Get current pipeline status"""
    try:
        status_service = PipelineStatusService()
        status = await status_service.get_status()
        activity = await status_service.get_activity_feed(limit=50)
        
        return {
            "status": status,
            "activity": activity,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting pipeline status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/stream")
async def stream_pipeline_status():
    """Stream real-time pipeline status updates via Server-Sent Events"""
    async def event_generator():
        status_service = PipelineStatusService()
        
        while True:
            try:
                status = await status_service.get_status()
                activity = await status_service.get_activity_feed(limit=10)
                
                data = {
                    "status": status,
                    "activity": activity,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                yield f"event: status\n"
                yield f"data: {json.dumps(data)}\n\n"
                
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Error in status stream: {e}")
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/metrics")
async def get_pipeline_metrics():
    """Get performance metrics for the pipeline"""
    try:
        status_service = PipelineStatusService()
        status = await status_service.get_status()
        
        # Calculate additional metrics
        stages = status.get("stages", {})
        rates = status.get("rates", {})
        
        # Calculate averages over different time ranges
        # For now, we'll use the current hour's data
        # In a production system, you'd want to aggregate over time
        
        metrics = {
            "current": {
                "collection_rate": rates.get("collection", 0),
                "analysis_rate": rates.get("analysis", 0),
                "posting_rate": rates.get("posting", 0),
            },
            "stages": {
                "collected": stages.get("collected", 0),
                "analyzed": stages.get("analyzed", 0),
                "rewritten": stages.get("rewritten", 0),
                "scheduled": stages.get("scheduled", 0),
                "posted": stages.get("posted", 0),
            },
            "health": status.get("health", "unknown"),
            "bottlenecks": status.get("bottlenecks", []),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return metrics
    except Exception as e:
        logger.error(f"Error getting pipeline metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

