#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
FastAPI Backend for BEYONDLINES
Extracted from Streamlit UI to provide REST API
"""

import os
import sys
from pathlib import Path

# CRITICAL: Add project root to path BEFORE any src imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Rate limiting - make optional (non-fatal if missing)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    SLOWAPI_AVAILABLE = True
except ImportError as e:
    # Demote to info so it doesn't spam scary warnings in dev
    logger.info(f"slowapi not installed - rate limiting disabled (this is fine in dev): {e}")
    SLOWAPI_AVAILABLE = False

    # Create dummy limiter if slowapi not available
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    Limiter = DummyLimiter

    def get_remote_address(request):
        return "127.0.0.1"

    class RateLimitExceeded(Exception):
        pass

    def _rate_limit_exceeded_handler(request, exc):
        return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)


from pydantic import BaseModel, field_validator

from src.api.routes import (
    analysis,
    collection,
    dashboard,
    observability,
    persona_studio,
    profiles,
    publishing,
    settings,
    system,
)
from src.utils.config import get_config
from src.utils.config_validator import (
    create_beyondlines_config_validator,
    validate_config,
)
from src.utils.error_handler import handle_errors

# Import custom error handling (now path is set up)
from src.utils.exceptions import (
    APIError,
    AuthenticationError,
    BEYONDLINESException,
    ConfigurationError,
    DatabaseError,
    RateLimitError,
    ValidationError,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Validate configuration at startup
logger.info("🔍 Validating configuration...")
try:
    config = get_config()
    config_dict = {
        "supabase_url": config.supabase_url,
        "supabase_service_role_key": config.supabase_service_role_key,
        "supabase_enabled": config.flags.get("supabase_enabled", True),
        "enable_analysis": config.flags.get("enable_analysis", True),
    }
    validator = create_beyondlines_config_validator()
    config_validation = validator.validate(config_dict)
    if not config_validation.is_valid:
        logger.warning(
            f"⚠️ Configuration validation found {len(config_validation.errors)} errors"
        )
        for error in config_validation.errors[:5]:  # Log first 5 errors
            logger.warning(f"   - {error}")
    else:
        logger.info("✅ Configuration validation completed")
except Exception as e:
    logger.warning(f"⚠️ Configuration validation error: {e} - continuing anyway")

# Initialize rate limiter (optional)
if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = Limiter()  # Dummy limiter
    # Don't log again here; the import block above already explained this once
security = HTTPBearer()

# Graceful shutdown helpers
import asyncio
import sys

_shutting_down = False


def handle_exception(loop, context):
    """Handle unhandled exceptions in asyncio tasks"""
    global _shutting_down

    exception = context.get("exception")
    if exception:
        # Suppress "Connection closed" errors during shutdown
        if isinstance(exception, Exception) and "Connection closed" in str(exception):
            if _shutting_down:
                logger.debug(f"Suppressing connection close error during shutdown")
                return
        # Suppress CancelledError during shutdown
        if isinstance(exception, asyncio.CancelledError):
            if _shutting_down:
                logger.debug("Suppressing CancelledError during shutdown")
                return
    # Log other exceptions only if not shutting down
    if not _shutting_down:
        logger.error(f"Unhandled exception in event loop: {context}")


def setup_exception_handler():
    """Setup exception handler for asyncio event loop"""
    try:
        loop = asyncio.get_running_loop()
        if loop:
            loop.set_exception_handler(handle_exception)
    except RuntimeError:
        # No running loop yet, will be set up later
        pass
    except Exception as e:
        logger.debug(f"Could not set exception handler: {e}")


async def graceful_shutdown():
    """Gracefully close all database connections and resources on shutdown"""
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True
    logger.info("🛑 Shutting down gracefully...")

    try:
        # Supabase and SQLite clean themselves up on process exit
        await asyncio.sleep(0.05)
        logger.info("✅ Graceful shutdown complete")
    except asyncio.CancelledError:
        # Swallow cancellations during shutdown
        logger.debug("Shutdown cancelled (expected during CTRL+C)")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        # Don't raise - we're shutting down anyway


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context for startup/shutdown"""
    setup_exception_handler()
    shutdown_run = False
    try:
        yield
    except asyncio.CancelledError:
        logger.debug("Lifespan cancelled - initiating shutdown")
        await graceful_shutdown()
        shutdown_run = True
        return
    finally:
        if not shutdown_run:
            await graceful_shutdown()


# Initialize FastAPI app
app = FastAPI(
    title="Beyondlines API",
    description="API for Beyondlines intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiting exception handler
if SLOWAPI_AVAILABLE:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Exception handlers
@app.exception_handler(BEYONDLINESException)
async def prisMind_exception_handler(request: Request, exc: BEYONDLINESException):
    """Handle BEYONDLINES custom exceptions"""
    logger.error(f"BEYONDLINES exception in {request.method} {request.url.path}: {exc}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": exc.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    """Handle database errors"""
    logger.error(f"Database error in {request.method} {request.url.path}: {exc}")

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": exc.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.exception_handler(APIError)
async def api_exception_handler(request: Request, exc: APIError):
    """Handle API errors"""
    logger.error(f"API error in {request.method} {request.url.path}: {exc}")

    return JSONResponse(
        status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY,
        content={
            "error": exc.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors"""
    logger.warning(
        f"Authentication error in {request.method} {request.url.path}: {exc}"
    )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": exc.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error in {request.method} {request.url.path}: {exc}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "error_type": "ValidationError",
                "message": "Request validation failed",
                "details": {
                    "validation_errors": exc.errors(),
                    "field_count": len(exc.errors()),
                },
            },
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        f"Unexpected error in {request.method} {request.url.path}: {exc}", exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "error_type": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {"error_type": type(exc).__name__, "message": str(exc)},
            },
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "method": request.method,
        },
    )


# CORS middleware - secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


# Pydantic models for request/response
class CollectionRequest(BaseModel):
    platform: Optional[str] = None  # None = collect all
    force: bool = False

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v):
        if v is not None and v not in ["twitter", "reddit", "threads"]:
            raise ValueError("Platform must be one of: twitter, reddit, threads")
        return v

    @field_validator("force")
    @classmethod
    def validate_force(cls, v):
        if not isinstance(v, bool):
            raise ValueError("Force must be a boolean")
        return v


class CollectionResponse(BaseModel):
    success: bool
    collected: int
    platform: str
    message: str


class PostResponse(BaseModel):
    id: str
    post_id: str
    platform: str
    content: str
    title: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    ai_summary: Optional[str] = None
    value_score: Optional[float] = None
    quality_score: Optional[float] = None


# Health check
@app.get("/api/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Basic health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}


@app.get("/api/health/detailed")
@limiter.limit("30/minute")
async def detailed_health_check(request: Request):
    """Detailed health check endpoint with system status"""
    from src.utils.circuit_breaker_wrapper import CircuitBreakerWrapper
    from src.utils.observability_hub import get_observability_hub

    hub = get_observability_hub()
    observability_health = hub.get_health_report()
    breakers = CircuitBreakerWrapper.get_all_status()
    open_breakers = [
        name for name, status in breakers.items() if status["state"] == "open"
    ]

    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "checks": {},
        "observability": {
            "metrics_count": observability_health["metrics"]["total_metrics"],
            "errors_count": observability_health["errors"]["total_errors"],
            "status": "healthy"
            if observability_health["errors"]["total_errors"] < 50
            else "degraded",
        },
        "circuit_breakers": {
            "total": len(breakers),
            "open": len(open_breakers),
            "status": "healthy" if not open_breakers else "degraded",
        },
    }

    # Check database connectivity
    try:
        from src.services.new_database_manager import NewDatabaseManager

        db = NewDatabaseManager()
        test_posts = db.get_posts(limit=1)
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except Exception as e:
        logger.error(f"Error checking database health: {e}")
        health_status["checks"]["database"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "degraded"

    # Check Supabase connectivity
    try:
        import os

        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if supabase_url and supabase_key:
            client = create_client(supabase_url, supabase_key)
            # Test with a simple query
            client.table("posts").select("count", count="exact").limit(1).execute()
            health_status["checks"]["supabase"] = {
                "status": "healthy",
                "message": "Supabase connection successful",
            }
        else:
            health_status["checks"]["supabase"] = {
                "status": "not_configured",
                "message": "Supabase credentials not provided",
            }
    except Exception as e:
        logger.error(f"Error checking Supabase health: {e}")
        health_status["checks"]["supabase"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "degraded"

    # Check AI services
    ai_services = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "gemini": "Google Gemini",
    }
    for service, name in ai_services.items():
        try:
            api_key = os.getenv(f"{service.upper()}_API_KEY")
            if api_key:
                health_status["checks"][service] = {
                    "status": "configured",
                    "message": f"{name} API key is configured",
                }
            else:
                health_status["checks"][service] = {
                    "status": "not_configured",
                    "message": f"{name} API key not provided",
                }
        except Exception as e:
            logger.error(f"Error checking {service} health: {e}")
            health_status["checks"][service] = {
                "status": "error",
                "message": f"Error checking {name} configuration",
            }

    # Check memory usage
    try:
        import psutil

        memory = psutil.virtual_memory()
        health_status["checks"]["memory"] = {
            "status": "healthy",
            "message": f"Memory usage: {memory.percent:.1f}%",
            "details": {
                "used_gb": round(memory.used / 1024**3, 2),
                "total_gb": round(memory.total / 1024**3, 2),
                "available_gb": round(memory.available / 1024**3, 2),
            },
        }
        if memory.percent > 90:
            health_status["checks"]["memory"]["status"] = "critical"
            health_status["status"] = "degraded"
        elif memory.percent > 80:
            health_status["checks"]["memory"]["status"] = "warning"
    except ImportError:
        logger.warning("⚠️ psutil not available for memory monitoring")
        health_status["checks"]["memory"] = {
            "status": "unknown",
            "message": "psutil not available for memory monitoring",
        }
    except Exception as e:
        logger.error(f"Error checking memory usage: {e}")
        health_status["checks"]["memory"] = {"status": "error", "message": str(e)}

    # Check disk space
    try:
        import psutil

        disk = psutil.disk_usage("/")
        health_status["checks"]["disk"] = {
            "status": "healthy",
            "message": f"Disk usage: {disk.percent:.1f}%",
            "details": {
                "used_gb": round(disk.used / 1024**3, 2),
                "total_gb": round(disk.total / 1024**3, 2),
                "free_gb": round(disk.free / 1024**3, 2),
            },
        }
        if disk.percent > 95:
            health_status["checks"]["disk"]["status"] = "critical"
            health_status["status"] = "degraded"
        elif disk.percent > 85:
            health_status["checks"]["disk"]["status"] = "warning"
    except ImportError:
        logger.warning("⚠️ psutil not available for disk monitoring")
        health_status["checks"]["disk"] = {
            "status": "unknown",
            "message": "psutil not available for disk monitoring",
        }
    except Exception as e:
        logger.error(f"Error checking disk usage: {e}")
        health_status["checks"]["disk"] = {"status": "error", "message": str(e)}

    return health_status


@app.get("/api/health/ready")
@limiter.limit("30/minute")
async def readiness_check(request: Request):
    """Readiness check endpoint for load balancers"""
    # Check critical dependencies
    try:
        from src.services.new_database_manager import NewDatabaseManager

        db = NewDatabaseManager()
        db.get_posts(limit=1)

        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "checks": {"database": "ready", "configuration": "ready"},
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "timestamp": datetime.now().isoformat(),
                "reason": str(e),
            },
        )


# Dashboard stats
@app.get("/api/dashboard/stats")
@limiter.limit("30/minute")
async def get_dashboard_stats(request: Request):
    """Get dashboard statistics"""
    try:
        from src.services.new_database_manager import NewDatabaseManager

        db = NewDatabaseManager()

        # Get basic counts
        all_posts = db.get_posts(limit=10000)
        total_posts = len(all_posts) if all_posts else 0

        # Count by platform
        platforms = {}
        unanalyzed = 0

        for post in all_posts or []:
            platform = post.get("platform", "unknown")
            platforms[platform] = platforms.get(platform, 0) + 1

            if not post.get("ai_summary") and not post.get("analyzed_at"):
                unanalyzed += 1

        return {
            "total_posts": total_posts,
            "platforms": platforms,
            "unanalyzed": unanalyzed,
            "analyzed": total_posts - unanalyzed,
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Posts endpoints
@app.get("/api/posts")
@limiter.limit("100/minute")
async def get_posts(
    request: Request,
    limit: int = 50,
    platform: Optional[str] = None,
    analyzed: Optional[bool] = None,
    offset: int = 0,
):
    """Get posts with filtering - queries Supabase directly"""
    try:
        import os

        from supabase import create_client

        # Query Supabase directly (primary source of truth)
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            logger.warning("Supabase credentials missing, falling back to SQLite")
            from src.services.new_database_manager import NewDatabaseManager

            db = NewDatabaseManager()
            posts = db.get_posts(limit=limit + offset)
            if not posts:
                return {"posts": [], "total": 0}
            filtered = posts
            if platform:
                filtered = [p for p in filtered if p.get("platform") == platform]
            if analyzed is not None:
                if analyzed:
                    filtered = [
                        p
                        for p in filtered
                        if p.get("ai_summary") or p.get("analyzed_at")
                    ]
                else:
                    filtered = [
                        p
                        for p in filtered
                        if not (p.get("ai_summary") or p.get("analyzed_at"))
                    ]
            paginated = filtered[offset : offset + limit]
            return {
                "posts": paginated,
                "total": len(filtered),
                "limit": limit,
                "offset": offset,
            }

        client = create_client(url, key)

        # Build query
        query = client.table("posts").select("*", count="exact")

        # Apply filters
        if platform:
            query = query.eq("platform", platform)

        if analyzed is not None:
            if analyzed:
                # Posts that have either ai_summary or analyzed_at - use PostgREST filter
                # We'll filter in Python after fetching since Supabase Python client has limited OR support
                pass  # Will filter after fetch
            else:
                # Posts that have neither
                query = query.is_("ai_summary", "null").is_("analyzed_at", "null")

        # If we need to filter for "analyzed" in Python, fetch more posts to account for filtering
        fetch_limit = limit * 3 if (analyzed is not None and analyzed) else limit

        # Apply ordering and pagination
        # Supabase range is inclusive: range(0, 9) returns 10 items (0-9)
        query = query.order("created_at", desc=True).range(
            offset, offset + fetch_limit - 1
        )

        # Get total count with a separate query
        try:
            count_query = client.table("posts").select("*", count="exact")
            if platform:
                count_query = count_query.eq("platform", platform)
            if analyzed is not None and not analyzed:
                count_query = count_query.is_("ai_summary", "null").is_(
                    "analyzed_at", "null"
                )
            count_resp = count_query.limit(1).execute()
            total = getattr(count_resp, "count", 0) or 0
        except Exception as e:
            logger.warning(f"Error getting total post count: {e}")
            total = 0

        response = query.execute()
        posts = response.data or []

        # Apply analyzed filter in Python if needed (for OR condition)
        if analyzed is not None and analyzed:
            posts = [p for p in posts if p.get("ai_summary") or p.get("analyzed_at")]
            # Apply pagination after filtering
            posts = posts[:limit]
            # Recalculate total for analyzed posts
            try:
                count_query = client.table("posts").select("*", count="exact")
                if platform:
                    count_query = count_query.eq("platform", platform)
                # Fetch a sample to count (more efficient than fetching all)
                all_sample = count_query.limit(1000).execute().data or []
                analyzed_count = len(
                    [
                        p
                        for p in all_sample
                        if p.get("ai_summary") or p.get("analyzed_at")
                    ]
                )
                # Estimate total if we got a good sample
                if len(all_sample) >= 1000:
                    # Rough estimate: ratio * total
                    ratio = analyzed_count / len(all_sample) if all_sample else 0
                    total = int(total * ratio) if total > 0 else analyzed_count
                else:
                    total = analyzed_count
            except Exception as e:
                logger.warning(f"Error getting analyzed count: {e}")
                total = len(posts)

        # Clean up post content - remove JSON metadata that might be in content field
        cleaned_posts = []
        import re

        def remove_json_blocks(text: str) -> str:
            """Remove JSON code blocks and JSON objects containing analysis metadata"""
            # Remove JSON code blocks (```json ... ``` or ``` ... ```)
            text = re.sub(
                r"```json\s*\{[\s\S]*?\}\s*```",
                "",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            text = re.sub(r"```\s*\{[\s\S]*?\}\s*```", "", text, flags=re.DOTALL)

            # Analysis metadata fields that should be removed
            analysis_fields = [
                "ai_summary",
                "tags",
                "key_concepts",
                "fit_categories",
                "value_score",
                "quality_score",
                "topic",
                "content_type",
                "language",
                "category",
            ]

            # Remove JSON objects that contain any analysis field
            # Use a more aggressive pattern that matches multi-line JSON
            for field in analysis_fields:
                # Match { ... "field": ... } - handles nested structures with DOTALL
                # This pattern will match from { to } even with nested braces (up to reasonable depth)
                pattern = (
                    r'\{(?:[^{}]|(?:\{[^{}]*\}))*?"'
                    + re.escape(field)
                    + r'"(?:[^{}]|(?:\{[^{}]*\}))*?\}'
                )
                text = re.sub(pattern, "", text, flags=re.DOTALL)

            # Remove any remaining JSON-like structures that look like metadata
            # Match patterns like { "key": "value", "key2": "value2" }
            text = re.sub(
                r'\{\s*"[^"]+"\s*:\s*"[^"]*"(?:\s*,\s*"[^"]+"\s*:\s*"[^"]*")*\s*\}',
                "",
                text,
                flags=re.DOTALL,
            )

            # Remove "=== TOP VALUABLE COMMENTS ===" and everything after
            text = re.sub(
                r"===.*?TOP.*?COMMENTS.*?===.*$",
                "",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )

            # Clean up whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            return text.strip()

        for post in posts:
            cleaned = dict(post)
            content = cleaned.get("content", "")

            if isinstance(content, str):
                cleaned["content"] = remove_json_blocks(content)

            cleaned_posts.append(cleaned)

        return {
            "posts": cleaned_posts,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error getting posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Collection endpoints
@app.post("/api/collection/start")
@limiter.limit("10/minute")
async def start_collection(
    payload: CollectionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Start collection for a platform or all platforms - runs in background"""
    try:
        from src.pipeline.orchestrator import get_orchestrator

        orch = get_orchestrator()

        if payload.platform:
            # Collect single platform in background
            async def collect_platform_task():
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"🚀 Starting {payload.platform} collection...")
                    logger.info(f"{'='*60}\n")
                    logger.info(f"Starting {payload.platform} collection")
                    count = await orch.collect_platform(payload.platform)
                    logger.info(f"\n{'='*60}")
                    logger.info(
                        f"✅ {payload.platform} collection complete: {count} posts"
                    )
                    logger.info(f"{'='*60}\n")
                    logger.info(
                        f"{payload.platform} collection complete: {count} posts"
                    )
                except Exception as e:
                    logger.error(f"\n❌ Error collecting {payload.platform}: {e}\n")
                    logger.error(
                        f"Error collecting {payload.platform}: {e}", exc_info=True
                    )

            background_tasks.add_task(collect_platform_task)
            return {
                "success": True,
                "collected": 0,  # Will be updated when task completes
                "platform": payload.platform,
                "message": f"Collection started for {payload.platform}",
            }
        else:
            # Collect all platforms in parallel (in background)
            import asyncio

            async def collect_all_platforms():
                async def collect_single(platform: str):
                    try:
                        logger.info(f"\n{'='*60}")
                        logger.info(f"🚀 Starting {platform} collection...")
                        logger.info(f"{'='*60}\n")
                        logger.info(f"Starting {platform} collection")
                        count = await orch.collect_platform(platform)
                        logger.info(
                            f"\n✅ {platform} collection complete: {count} posts\n"
                        )
                        logger.info(f"{platform} collection complete: {count} posts")
                    except Exception as e:
                        logger.error(f"\n❌ Error collecting {platform}: {e}\n")
                        logger.error(f"Error collecting {platform}: {e}", exc_info=True)

                logger.info(f"\n{'='*60}")
                logger.info(f"🚀 Starting FULL SWEEP - All platforms")
                logger.info(f"{'='*60}\n")
                logger.info("Starting full sweep collection")

                # Run all collections in parallel
                platform_list = ["twitter", "reddit", "threads"]
                await asyncio.gather(*[collect_single(p) for p in platform_list])

                logger.info(f"\n{'='*60}")
                logger.info(f"✅ FULL SWEEP complete")
                logger.info(f"{'='*60}\n")
                logger.info("Full sweep collection complete")

            background_tasks.add_task(collect_all_platforms)
            return {
                "success": True,
                "collected": 0,  # Will be updated when tasks complete
                "platform": "all",
                "message": "Full sweep started - all platforms collecting in parallel",
                "platforms": [],
            }
    except Exception as e:
        logger.error(f"Error starting collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Include routers
app.include_router(publishing.router)
app.include_router(collection.router)
app.include_router(analysis.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(observability.router)
app.include_router(system.router)
app.include_router(profiles.router)
app.include_router(persona_studio.router)


if __name__ == "__main__":
    import uvicorn

    logger.info("\n" + "=" * 60)
    logger.info("🚀 Starting BEYONDLINES FastAPI Backend")
    logger.info("=" * 60)
    logger.info("📡 API will be available at: http://localhost:8000")
    logger.info("📚 API docs at: http://localhost:8000/docs")
    logger.info("=" * 60 + "\n")
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",  # Show INFO level logs
            access_log=True,  # Show access logs
        )
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
