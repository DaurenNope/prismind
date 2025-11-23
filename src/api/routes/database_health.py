#!/usr/bin/env python3
"""
Database Health Dashboard API
==============================
API endpoints for database health monitoring and query performance
Created: 2025-11-20
Priority: P2 - Observability

Endpoints:
    GET /api/database/health - Overall database health
    GET /api/database/queries/stats - Query performance statistics
    GET /api/database/queries/slow - Slow query reports
    GET /api/database/consistency - Database consistency check
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.infrastructure.database.query_monitor import (
    get_query_stats,
    get_query_summary,
    get_slow_queries,
    SLOW_QUERY_THRESHOLD_MS,
)
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/database", tags=["database"])


# Response models
class QueryStat(BaseModel):
    count: int
    avg_ms: float
    min_ms: float
    max_ms: float
    total_ms: float


class QueryStatsResponse(BaseModel):
    total_queries: int
    unique_queries: int
    total_time_ms: float
    avg_time_ms: float
    slow_queries_count: int
    query_stats: Dict[str, QueryStat]
    top_slow_queries: List[Dict[str, Any]]


class SlowQueryResponse(BaseModel):
    name: str
    time_ms: float
    timestamp: str
    type: str
    row_count: Optional[int] = None


class DatabaseHealthResponse(BaseModel):
    status: str
    timestamp: str
    database_status: Dict[str, Any]
    query_performance: Dict[str, Any]
    consistency: Optional[Dict[str, Any]] = None


class ConsistencyResponse(BaseModel):
    consistent: bool
    row_counts: Dict[str, int]
    schema_consistency: Dict[str, Any]
    data_drift: Dict[str, Any]
    timestamp: str


@router.get("/health", response_model=DatabaseHealthResponse)
async def get_database_health():
    """
    Get overall database health status
    
    Returns:
        Overall health status including database connection, query performance, and consistency
    """
    try:
        # Get query summary
        query_summary = get_query_summary()
        
        # Check database connections
        database_status = {
            'supabase_connected': False,
            'sqlite_connected': False,
        }
        
        try:
            from src.infrastructure.database.manager import SupabaseManager
            manager = SupabaseManager()
            # Try a simple query
            manager.client.table('posts').select('id').limit(1).execute()
            database_status['supabase_connected'] = True
        except Exception as e:
            logger.warning(f"Supabase connection check failed: {e}")
            database_status['supabase_error'] = str(e)
        
        try:
            import sqlite3
            with sqlite3.connect("beyondlines.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                database_status['sqlite_connected'] = True
        except Exception as e:
            logger.warning(f"SQLite connection check failed: {e}")
            database_status['sqlite_error'] = str(e)
        
        # Determine overall status
        all_connected = database_status.get('supabase_connected', False)
        has_slow_queries = query_summary['slow_queries_count'] > 0
        avg_time_ok = query_summary['avg_time_ms'] < SLOW_QUERY_THRESHOLD_MS
        
        if all_connected and not has_slow_queries and avg_time_ok:
            status = "healthy"
        elif all_connected:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return DatabaseHealthResponse(
            status=status,
            timestamp=datetime.now().isoformat(),
            database_status=database_status,
            query_performance={
                'total_queries': query_summary['total_queries'],
                'avg_time_ms': query_summary['avg_time_ms'],
                'slow_queries_count': query_summary['slow_queries_count'],
            },
        )
        
    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/stats", response_model=QueryStatsResponse)
async def get_query_stats_endpoint():
    """
    Get query performance statistics
    
    Returns:
        Detailed query performance statistics
    """
    try:
        summary = get_query_summary()
        
        # Convert query_stats to response format
        query_stats = {
            name: QueryStat(**stats)
            for name, stats in summary['query_stats'].items()
        }
        
        return QueryStatsResponse(
            total_queries=summary['total_queries'],
            unique_queries=summary['unique_queries'],
            total_time_ms=summary['total_time_ms'],
            avg_time_ms=summary['avg_time_ms'],
            slow_queries_count=summary['slow_queries_count'],
            query_stats=query_stats,
            top_slow_queries=summary['top_slow_queries'],
        )
        
    except Exception as e:
        logger.error(f"Error getting query stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/slow", response_model=List[SlowQueryResponse])
async def get_slow_queries_endpoint(
    limit: Optional[int] = Query(default=10, ge=1, le=100),
    min_time_ms: Optional[float] = Query(default=SLOW_QUERY_THRESHOLD_MS, ge=0),
):
    """
    Get slow query reports
    
    Args:
        limit: Maximum number of slow queries to return (1-100)
        min_time_ms: Minimum execution time to include
    
    Returns:
        List of slow queries
    """
    try:
        slow_queries = get_slow_queries(limit=limit, min_time_ms=min_time_ms)
        
        return [
            SlowQueryResponse(
                name=q['name'],
                time_ms=q['time_ms'],
                timestamp=q['timestamp'],
                type=q['type'],
                row_count=q.get('row_count'),
            )
            for q in slow_queries
        ]
        
    except Exception as e:
        logger.error(f"Error getting slow queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consistency", response_model=ConsistencyResponse)
async def check_consistency():
    """
    Check database consistency between Supabase and SQLite
    
    Returns:
        Consistency check results
    """
    try:
        # Import consistency checker functions
        from scripts.database.check_consistency import (
            check_row_counts,
            check_schema_consistency,
            check_data_drift,
        )
        
        # Run checks
        row_counts = check_row_counts()
        schema_consistency = check_schema_consistency()
        data_drift = check_data_drift(sample_size=100)
        
        # Determine overall consistency
        consistent = (
            row_counts['consistent'] and
            schema_consistency['consistent'] and
            data_drift['drift_percentage'] < 5.0
        )
        
        return ConsistencyResponse(
            consistent=consistent,
            row_counts={
                'supabase': row_counts['supabase_count'],
                'sqlite': row_counts['sqlite_count'],
                'difference': row_counts['difference'],
            },
            schema_consistency={
                'consistent': schema_consistency['consistent'],
                'missing_in_sqlite': schema_consistency['missing_in_sqlite'],
                'missing_in_supabase': schema_consistency['missing_in_supabase'],
            },
            data_drift={
                'checked': data_drift['checked'],
                'matches': data_drift['matches'],
                'mismatches': data_drift['mismatches'],
                'drift_percentage': data_drift['drift_percentage'],
            },
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as e:
        logger.error(f"Error checking consistency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional utility endpoints
@router.post("/queries/clear-stats")
async def clear_query_stats():
    """Clear query statistics (useful for testing)"""
    try:
        from src.infrastructure.database.query_monitor import clear_stats
        clear_stats()
        return {"message": "Query statistics cleared"}
    except Exception as e:
        logger.error(f"Error clearing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/performance-trends")
async def get_performance_trends(
    hours: int = Query(default=24, ge=1, le=168),  # 1 hour to 7 days
):
    """
    Get query performance trends over time
    
    Note: This is a placeholder - would need time-series storage for full implementation
    Currently returns current stats as trends would require persistent storage
    
    Args:
        hours: Number of hours to look back
    
    Returns:
        Performance trends (current implementation returns current stats)
    """
    try:
        summary = get_query_summary()
        
        return {
            "period_hours": hours,
            "current_stats": {
                "total_queries": summary['total_queries'],
                "avg_time_ms": summary['avg_time_ms'],
                "slow_queries_count": summary['slow_queries_count'],
            },
            "note": "Time-series storage not implemented yet - returns current stats",
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))






