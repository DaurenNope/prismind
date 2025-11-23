"""
Error Dashboard API Routes
Handles error tracking, viewing, and resolution
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.shared.utils.logging_config import get_logger
from src.services.error_tracker import get_error_tracker

logger = get_logger(__name__)

router = APIRouter(prefix="/api/errors", tags=["errors"])


# Request/Response models
class ResolveErrorRequest(BaseModel):
    resolution_notes: Optional[str] = None


@router.get("")
async def get_errors(
    component: Optional[str] = Query(None, description="Filter by component"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(50, ge=1, le=200, description="Number of errors to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get list of errors with filters"""
    try:
        error_tracker = get_error_tracker()
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        result = error_tracker.get_errors(
            component=component,
            severity=severity,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit,
            offset=offset
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting errors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{error_id}")
async def get_error_details(error_id: str):
    """Get full error details including stack trace"""
    try:
        error_tracker = get_error_tracker()
        error = error_tracker.get_error_details(error_id)
        
        if not error:
            raise HTTPException(status_code=404, detail="Error not found")
        
        return {"error": error}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting error details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_error_stats():
    """Get error statistics"""
    try:
        error_tracker = get_error_tracker()
        stats = error_tracker.get_error_stats()
        
        return stats
    except Exception as e:
        logger.error(f"Error getting error stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{error_id}/resolve")
async def resolve_error(error_id: str, request: ResolveErrorRequest):
    """Mark error as resolved"""
    try:
        error_tracker = get_error_tracker()
        
        # Check if error exists
        error = error_tracker.get_error_details(error_id)
        if not error:
            raise HTTPException(status_code=404, detail="Error not found")
        
        # Resolve error
        success = error_tracker.resolve_error(error_id, request.resolution_notes)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to resolve error")
        
        # Get updated error
        updated_error = error_tracker.get_error_details(error_id)
        
        return {
            "success": True,
            "error": updated_error
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

