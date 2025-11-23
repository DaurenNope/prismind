from __future__ import annotations

import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from rq.job import Job

from services.common import tasks
from services.common.job_queue import get_queue, get_redis_connection

app = FastAPI(title="Prismind Control API", version="1.0.0")

# Queue name constants
COLLECTOR_THREADS_QUEUE = os.getenv("QUEUE_COLLECTOR_THREADS", "collector_threads")
COLLECTOR_TWITTER_QUEUE = os.getenv("QUEUE_COLLECTOR_TWITTER", "collector_twitter")
REWRITER_QUEUE = os.getenv("QUEUE_REWRITER", "rewriter")
PUBLISHER_QUEUE = os.getenv("QUEUE_PUBLISHER", "publisher")


class CollectRequest(BaseModel):
    platform: str = Field(..., pattern="^(threads|twitter)$")
    force_once: bool = False


class BacklogRequest(BaseModel):
    profiles: Optional[List[str]] = None
    posts_per_profile: Optional[int] = Field(None, ge=1)


class JobStatusResponse(BaseModel):
    id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


@app.post("/jobs/collect", response_model=JobStatusResponse)
def enqueue_collection(req: CollectRequest):
    queue_name = (
        COLLECTOR_THREADS_QUEUE
        if req.platform == "threads"
        else COLLECTOR_TWITTER_QUEUE
    )
    queue = get_queue(queue_name)
    job = queue.enqueue(
        tasks.collect_platform,
        kwargs={"platform": req.platform, "force_once": req.force_once},
        retry=None,
        result_ttl=3600,
        description=f"collect_{req.platform}",
    )
    return JobStatusResponse(id=job.id, status=job.get_status())


@app.post("/jobs/process_backlog", response_model=JobStatusResponse)
def enqueue_backlog(req: BacklogRequest):
    queue = get_queue(REWRITER_QUEUE)
    job = queue.enqueue(
        tasks.process_backlog,
        kwargs={"profiles": req.profiles, "posts_per_profile": req.posts_per_profile},
        retry=None,
        result_ttl=3600,
        description="process_backlog",
    )
    return JobStatusResponse(id=job.id, status=job.get_status())


@app.post("/jobs/publish_due", response_model=JobStatusResponse)
def enqueue_publish():
    queue = get_queue(PUBLISHER_QUEUE)
    job = queue.enqueue(
        tasks.publish_due,
        kwargs={},
        retry=None,
        result_ttl=3600,
        description="publish_due",
    )
    return JobStatusResponse(id=job.id, status=job.get_status())


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=get_redis_connection())
    except (RedisError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    response = JobStatusResponse(id=job.id, status=job.get_status())
    if job.is_finished:
        response.result = (
            job.result if isinstance(job.result, dict) else {"result": job.result}
        )
    elif job.is_failed:
        response.error = str(job.exc_info) if job.exc_info else "Job failed"
    return response


@app.get("/health/live")
def liveness_check():
    """
    Liveness probe endpoint.
    Returns 200 if the service is alive (process is running).
    Kubernetes will restart the container if this fails.
    """
    from datetime import datetime

    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "prismind-api",
    }


@app.get("/health")
def healthcheck():
    """Comprehensive health check for BEYONDLINES API service"""
    import platform
    from datetime import datetime

    import psutil

    health_info = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "BEYONDLINES API",
        "checks": {},
    }

    # Check Redis connection
    try:
        import time

        start_time = time.time()
        conn = get_redis_connection()
        redis_result = conn.ping()
        response_time_ms = (time.time() - start_time) * 1000
        health_info["checks"]["redis"] = {
            "status": "healthy" if redis_result else "unhealthy",
            "response_time_ms": round(response_time_ms, 2),
        }
    except RedisError as exc:
        health_info["checks"]["redis"] = {"status": "unhealthy", "error": str(exc)}
        health_info["status"] = "degraded"

    # Check system resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        health_info["checks"]["system"] = {
            "status": "healthy",
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory.percent, 2),
            "disk_percent": round(disk.percent, 2),
        }

        # Set status to degraded if resources are high
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            health_info["status"] = "degraded"

    except Exception as exc:
        health_info["checks"]["system"] = {"status": "error", "error": str(exc)}

    # Check job queues
    try:
        queue_status = {}
        for queue_name in [
            COLLECTOR_THREADS_QUEUE,
            COLLECTOR_TWITTER_QUEUE,
            REWRITER_QUEUE,
            PUBLISHER_QUEUE,
        ]:
            try:
                queue = get_queue(queue_name)
                queue_status[queue_name] = {
                    "status": "healthy",
                    "pending_jobs": len(queue),
                    "failed_jobs": queue.failed_job_registry.count,
                }
            except Exception as exc:
                queue_status[queue_name] = {"status": "error", "error": str(exc)}

        health_info["checks"]["queues"] = queue_status

    except Exception as exc:
        health_info["checks"]["queues"] = {"status": "error", "error": str(exc)}
        health_info["status"] = "degraded"

    # Return appropriate HTTP status
    if health_info["status"] == "healthy":
        return health_info
    elif health_info["status"] == "degraded":
        raise HTTPException(
            status_code=200, detail=health_info
        )  # Still serving but degraded
    else:
        raise HTTPException(status_code=503, detail=health_info)  # Service unavailable


@app.get("/health/ready")
def readiness_check():
    """Readiness check for Kubernetes/container orchestration"""
    from datetime import datetime

    try:
        # Check if Redis is accessible
        conn = get_redis_connection()
        conn.ping()

        # Check if we can access job queues
        for queue_name in [
            COLLECTOR_THREADS_QUEUE,
            COLLECTOR_TWITTER_QUEUE,
            REWRITER_QUEUE,
            PUBLISHER_QUEUE,
        ]:
            get_queue(queue_name)

        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail={"status": "not_ready", "error": str(exc)}
        )
