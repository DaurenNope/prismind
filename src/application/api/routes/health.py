"""
Enhanced Health Check Endpoints
==============================

Provides comprehensive health checks for Kubernetes/container orchestration:
- /health/live - Liveness probe (is the service alive?)
- /health/ready - Readiness probe (is the service ready to serve traffic?)
- /health - Comprehensive health check with detailed status

Author: Prismind Production Team
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

import psutil
from fastapi import APIRouter, HTTPException
from redis.exceptions import RedisError

from services.common.job_queue import get_queue, get_redis_connection
from src.monitoring.error_tracker import get_error_tracker
from src.monitoring.metrics import get_metrics_collector
from src.monitoring.performance_monitor import get_performance_monitor
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Service configuration
COLLECTOR_THREADS_QUEUE = "collector_threads"
COLLECTOR_TWITTER_QUEUE = "collector_twitter"
REWRITER_QUEUE = "rewriter"
PUBLISHER_QUEUE = "publisher"


def check_redis() -> Dict[str, Any]:
    """Check Redis connection"""
    try:
        start_time = time.time()
        conn = get_redis_connection()
        conn.ping()
        response_time_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "response_time_ms": round(response_time_ms, 2),
            "error": None,
        }
    except RedisError as e:
        return {
            "status": "unhealthy",
            "response_time_ms": None,
            "error": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time_ms": None,
            "error": str(e),
        }


def check_database() -> Dict[str, Any]:
    """Check database connection"""
    try:
        start_time = time.time()

        # Try to import and check database
        from src.services.new_database_manager import get_database_manager

        db = get_database_manager()
        # Simple read operation to verify connection
        db.get_posts(limit=1)

        response_time_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "response_time_ms": round(response_time_ms, 2),
            "error": None,
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time_ms": None,
            "error": str(e),
        }


def check_job_queues() -> Dict[str, Dict[str, Any]]:
    """Check job queue status"""
    queues_status = {}
    queue_names = [
        COLLECTOR_THREADS_QUEUE,
        COLLECTOR_TWITTER_QUEUE,
        REWRITER_QUEUE,
        PUBLISHER_QUEUE,
    ]

    for queue_name in queue_names:
        try:
            queue = get_queue(queue_name)
            queues_status[queue_name] = {
                "status": "healthy",
                "pending_jobs": len(queue),
                "failed_jobs": queue.failed_job_registry.count,
                "error": None,
            }
        except Exception as e:
            queues_status[queue_name] = {
                "status": "error",
                "pending_jobs": None,
                "failed_jobs": None,
                "error": str(e),
            }

    return queues_status


def check_system_resources() -> Dict[str, Any]:
    """Check system resource usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        status = "healthy"
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = "degraded"

        return {
            "status": status,
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory.percent, 2),
            "memory_used_mb": round(memory.used / (1024 * 1024), 2),
            "disk_percent": round(disk.percent, 2),
            "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/live")
def liveness_check() -> Dict[str, str]:
    """
    Liveness probe endpoint.
    Returns 200 if the service is alive (process is running).
    Kubernetes will restart the container if this fails.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "prismind-api",
    }


@router.get("/ready")
def readiness_check() -> Dict[str, Any]:
    """
    Readiness probe endpoint.
    Returns 200 if the service is ready to serve traffic.
    Returns 503 if dependencies are not ready.
    """
    checks = {
        "redis": check_redis(),
    }

    # Determine overall readiness
    all_healthy = all(
        check.get("status") == "healthy" for check in checks.values()
    )

    if not all_healthy:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": checks,
            },
        )

    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("")
def comprehensive_health() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    Returns detailed status of all components.
    """
    checks = {
        "redis": check_redis(),
        "database": check_database(),
        "job_queues": check_job_queues(),
        "system_resources": check_system_resources(),
    }

    # Get metrics summary
    metrics_collector = get_metrics_collector()
    metrics_summary = metrics_collector.get_metrics_summary(hours=1)

    # Get performance monitor status
    perf_monitor = get_performance_monitor()
    dashboard_data = perf_monitor.get_dashboard_data()

    # Determine overall status
    critical_checks = ["redis"]
    degraded_checks = ["database", "system_resources"]

    status = "healthy"
    for check_name in critical_checks:
        if check_name in checks:
            check_status = checks[check_name].get("status", "unknown")
            if check_status not in ["healthy"]:
                status = "unhealthy"
                break

    if status == "healthy":
        for check_name in degraded_checks:
            if check_name in checks:
                check_status = checks[check_name].get("status", "unknown")
                if check_status == "degraded":
                    status = "degraded"
                    break

    response = {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "prismind-api",
        "version": "1.0.0",
        "checks": checks,
        "metrics": {
            "summary": metrics_summary,
            "system_status": dashboard_data.get("system_status", "unknown"),
        },
    }

    # Return appropriate HTTP status
    if status == "healthy":
        return response
    elif status == "degraded":
        # Still return 200 but with degraded status
        return response
    else:
        raise HTTPException(status_code=503, detail=response)


@router.get("/metrics")
def metrics_endpoint() -> Dict[str, Any]:
    """Get detailed metrics for monitoring dashboards"""
    metrics_collector = get_metrics_collector()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": metrics_collector.get_metrics_summary(hours=1),
        "database_performance": metrics_collector.get_database_performance(hours=1),
    }






