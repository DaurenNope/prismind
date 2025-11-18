"""
API Gateway for Beyondlines
Provides centralized request routing, rate limiting, and middleware management
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientSession, ClientTimeout, web
from aiohttp.web import Request, Response, middleware

from ..observability.tracing import (
    get_trace_headers,
    set_trace_from_headers,
    trace_function,
    tracer,
)
from ..resilience.circuit_breaker import CircuitBreaker, circuit_breaker_registry
from ..utils.exceptions import GatewayError, RateLimitExceededError

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RouteConfig:
    """Configuration for a route"""

    path: str
    method: str
    target_url: str
    timeout: float = 30.0
    retries: int = 3
    circuit_breaker: Optional[CircuitBreaker] = None
    rate_limit: Optional[int] = None  # requests per minute
    auth_required: bool = False
    allowed_origins: List[str] = field(default_factory=list)
    transform_request: Optional[Callable] = None
    transform_response: Optional[Callable] = None


@dataclass
class RateLimitEntry:
    """Entry for rate limiting"""

    count: int
    window_start: float
    last_request: float


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self, strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW):
        self.strategy = strategy
        self._limits: Dict[str, RateLimitEntry] = defaultdict(
            lambda: RateLimitEntry(0, 0, 0)
        )
        self._lock = asyncio.Lock()

    async def is_allowed(
        self, key: str, limit: int, window: int = 60
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed"""
        now = time.time()

        async with self._lock:
            entry = self._limits[key]

            if self.strategy == RateLimitStrategy.FIXED_WINDOW:
                return self._fixed_window_check(entry, limit, window, now)
            elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._sliding_window_check(entry, limit, window, now)
            elif self.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._token_bucket_check(entry, limit, window, now)

        return True, {"remaining": limit, "reset_time": now + window}

    def _fixed_window_check(
        self, entry: RateLimitEntry, limit: int, window: int, now: float
    ) -> tuple[bool, Dict[str, Any]]:
        """Fixed window rate limiting"""
        if now - entry.window_start >= window:
            entry.count = 0
            entry.window_start = now

        entry.count += 1
        allowed = entry.count <= limit

        remaining = max(0, limit - entry.count)
        reset_time = entry.window_start + window

        return allowed, {
            "remaining": remaining,
            "reset_time": reset_time,
            "current": entry.count,
        }

    def _sliding_window_check(
        self, entry: RateLimitEntry, limit: int, window: int, now: float
    ) -> tuple[bool, Dict[str, Any]]:
        """Sliding window rate limiting"""
        # For simplicity, this is a basic implementation
        # In production, you'd want a more sophisticated approach
        entry.count += 1
        entry.last_request = now

        # Decay old requests
        if now - entry.window_start >= window:
            entry.count = 1
            entry.window_start = now

        allowed = entry.count <= limit
        remaining = max(0, limit - entry.count)

        return allowed, {
            "remaining": remaining,
            "reset_time": now + window,
            "current": entry.count,
        }

    def _token_bucket_check(
        self, entry: RateLimitEntry, limit: int, window: int, now: float
    ) -> tuple[bool, Dict[str, Any]]:
        """Token bucket rate limiting"""
        # Simplified token bucket implementation
        tokens = limit
        refill_rate = limit / window

        # Refill tokens based on time passed
        if entry.last_request > 0:
            time_passed = now - entry.last_request
            tokens = min(limit, tokens + time_passed * refill_rate)

        if tokens >= 1:
            tokens -= 1
            entry.last_request = now
            return True, {"remaining": int(tokens), "reset_time": now + window}
        else:
            wait_time = (1 - tokens) / refill_rate
            return False, {"retry_after": wait_time}


class APIGateway:
    """Main API Gateway implementation"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application(
            middlewares=[
                self.cors_middleware,
                self.rate_limit_middleware,
                self.auth_middleware,
                self.tracing_middleware,
                self.metrics_middleware,
            ]
        )
        self.routes: Dict[str, RouteConfig] = {}
        self.rate_limiter = RateLimiter()
        self.session: Optional[ClientSession] = None
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited_requests": 0,
            "circuit_breaker_trips": 0,
        }

    async def start(self):
        """Start the API Gateway"""
        self.session = ClientSession(
            timeout=ClientTimeout(total=60), connector=aiohttp.TCPConnector(limit=100)
        )

        # Add health check endpoint
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/metrics", self.get_metrics)
        self.app.router.add_get("/routes", self.list_routes)

        # Add catch-all route
        self.app.router.add_route("*", "/{path:.*}", self.proxy_handler)

        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"API Gateway started on {self.host}:{self.port}")

    async def stop(self):
        """Stop the API Gateway"""
        if self.session:
            await self.session.close()
        logger.info("API Gateway stopped")

    def add_route(self, config: RouteConfig):
        """Add a route configuration"""
        key = f"{config.method.upper()}:{config.path}"
        self.routes[key] = config
        logger.info(f"Added route: {key} -> {config.target_url}")

    @middleware
    async def cors_middleware(self, request: Request, handler: Callable):
        """CORS middleware"""
        origin = request.headers.get("Origin", "")

        # Check if origin is allowed
        route_key = f"{request.method}:{request.path_info}"
        allowed_origins = ["*"]  # Default

        if route_key in self.routes:
            route = self.routes[route_key]
            if route.allowed_origins:
                allowed_origins = route.allowed_origins

        if allowed_origins == ["*"] or origin in allowed_origins:
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = (
                origin if origin != "*" else "*"
            )
            response.headers[
                "Access-Control-Allow-Methods"
            ] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, X-Trace-ID"
            return response

        return await handler(request)

    @middleware
    async def rate_limit_middleware(self, request: Request, handler: Callable):
        """Rate limiting middleware"""
        # Get client identifier
        client_id = self._get_client_id(request)

        # Check route-specific rate limits
        route_key = f"{request.method}:{request.path_info}"
        rate_limit = None

        if route_key in self.routes:
            rate_limit = self.routes[route_key].rate_limit

        # Apply rate limiting if configured
        if rate_limit:
            allowed, info = await self.rate_limiter.is_allowed(client_id, rate_limit)

            if not allowed:
                self.metrics["rate_limited_requests"] += 1
                retry_after = info.get("retry_after", 60)

                raise web.HTTPTooManyRequests(
                    text=json.dumps(
                        {"error": "Rate limit exceeded", "retry_after": retry_after}
                    ),
                    headers={"Retry-After": str(retry_after)},
                )

        return await handler(request)

    @middleware
    async def auth_middleware(self, request: Request, handler: Callable):
        """Authentication middleware"""
        route_key = f"{request.method}:{request.path_info}"

        if route_key in self.routes:
            route = self.routes[route_key]
            if route.auth_required:
                # Check for API key or JWT token
                auth_header = request.headers.get("Authorization", "")
                if not self._validate_auth(auth_header):
                    raise web.HTTPUnauthorized(
                        text=json.dumps({"error": "Authentication required"})
                    )

        return await handler(request)

    @middleware
    async def tracing_middleware(self, request: Request, handler: Callable):
        """Distributed tracing middleware"""
        # Extract trace headers
        trace_headers = {
            "x-trace-id": request.headers.get("x-trace-id"),
            "x-span-id": request.headers.get("x-span-id"),
            "x-parent-span-id": request.headers.get("x-parent-span-id"),
        }

        # Set trace context if headers exist
        if trace_headers["x-trace-id"]:
            set_trace_from_headers({k: v for k, v in trace_headers.items() if v})

        # Start span for request
        with tracer.trace_async(
            f"gateway:{request.method}:{request.path_info}", kind=tracer.SpanKind.SERVER
        ) as span:
            span.set_tag("http.method", request.method)
            span.set_tag("http.url", str(request.url))
            span.set_tag("http.user_agent", request.headers.get("User-Agent", ""))
            span.set_tag("client.ip", self._get_client_ip(request))

            try:
                response = await handler(request)
                span.set_tag("http.status_code", response.status)
                return response
            except Exception as e:
                logger.error(f"Error: {e}")
                span.set_status(tracer.SpanStatus.ERROR, str(e))
                raise

    @middleware
    async def metrics_middleware(self, request: Request, handler: Callable):
        """Metrics collection middleware"""
        start_time = time.time()
        self.metrics["total_requests"] += 1

        try:
            response = await handler(request)
            self.metrics["successful_requests"] += 1
            return response
        except Exception as e:
            logger.error(f"Error: {e}")
            self.metrics["failed_requests"] += 1
            raise
        finally:
            duration = (time.time() - start_time) * 1000
            logger.debug(
                f"Request {request.method} {request.path_info} took {duration:.2f}ms"
            )

    async def proxy_handler(self, request: Request) -> Response:
        """Main request proxy handler"""
        route_key = f"{request.method}:{request.path_info}"

        if route_key not in self.routes:
            raise web.HTTPNotFound(text=json.dumps({"error": "Route not found"}))

        route = self.routes[route_key]

        try:
            return await self._proxy_request(request, route)
        except Exception as e:
            logger.error(f"Proxy error for {route_key}: {e}")
            raise web.HTTPGatewayTimeout(text=json.dumps({"error": "Gateway error"}))

    async def _proxy_request(self, request: Request, route: RouteConfig) -> Response:
        """Proxy individual request"""
        # Prepare target URL
        target_url = route.target_url

        # Add query parameters
        if request.query_string:
            target_url += f"?{request.query_string}"

        # Prepare headers
        headers = dict(request.headers)
        headers.update(get_trace_headers())

        # Remove hop-by-hop headers
        hop_by_hop = {
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
            "host",
        }
        headers = {k: v for k, v in headers.items() if k.lower() not in hop_by_hop}

        # Transform request if needed
        if route.transform_request:
            request_data = await route.transform_request(request)
        else:
            if request.method in ["POST", "PUT", "PATCH"]:
                request_data = await request.read()
            else:
                request_data = None

        # Make request with circuit breaker if configured
        if route.circuit_breaker:
            async with route.circuit_breaker:
                response = await self.session.request(
                    request.method,
                    target_url,
                    headers=headers,
                    data=request_data,
                    timeout=route.timeout,
                )
        else:
            response = await self.session.request(
                request.method,
                target_url,
                headers=headers,
                data=request_data,
                timeout=route.timeout,
            )

        # Read response
        response_data = await response.read()

        # Transform response if needed
        if route.transform_response:
            response_data = await route.transform_response(response_data, response)

        # Prepare response headers
        response_headers = dict(response.headers)
        response_headers.pop("content-length", None)
        response_headers.pop("transfer-encoding", None)

        return Response(
            body=response_data, status=response.status, headers=response_headers
        )

    async def health_check(self, request: Request) -> Response:
        """Health check endpoint"""
        health = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0",
            "routes": len(self.routes),
            "circuit_breakers": {
                "open": len(
                    circuit_breaker_registry.get_breakers_by_state(
                        circuit_breaker_registry.CircuitState.OPEN
                    )
                ),
                "closed": len(
                    circuit_breaker_registry.get_breakers_by_state(
                        circuit_breaker_registry.CircuitState.CLOSED
                    )
                ),
                "half_open": len(
                    circuit_breaker_registry.get_breakers_by_state(
                        circuit_breaker_registry.CircuitState.HALF_OPEN
                    )
                ),
            },
        }

        return Response(
            text=json.dumps(health, indent=2), content_type="application/json"
        )

    async def get_metrics(self, request: Request) -> Response:
        """Get gateway metrics"""
        return Response(
            text=json.dumps(self.metrics, indent=2), content_type="application/json"
        )

    async def list_routes(self, request: Request) -> Response:
        """List all configured routes"""
        routes_info = {}
        for key, config in self.routes.items():
            routes_info[key] = {
                "target": config.target_url,
                "timeout": config.timeout,
                "rate_limit": config.rate_limit,
                "auth_required": config.auth_required,
            }

        return Response(
            text=json.dumps(routes_info, indent=2), content_type="application/json"
        )

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Use API key if available, then IP address
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"

        # Use IP address
        ip = self._get_client_ip(request)
        return f"ip:{ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to remote address
        return request.remote or "unknown"

    def _validate_auth(self, auth_header: str) -> bool:
        """Validate authentication header"""
        if not auth_header:
            return False

        # Basic validation - in production, implement proper JWT or API key validation
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Validate token here
            return len(token) > 10

        return False


# Gateway configuration helper
def create_gateway_config() -> List[RouteConfig]:
    """Create default gateway route configurations"""
    routes = [
        RouteConfig(
            path="/api/{path:.*}",
            method="GET",
            target_url="http://api:8000/api/{path}",
            timeout=30.0,
            rate_limit=100,  # 100 requests per minute
            auth_required=False,
            allowed_origins=["*"],
        ),
        RouteConfig(
            path="/api/{path:.*}",
            method="POST",
            target_url="http://api:8000/api/{path}",
            timeout=60.0,
            rate_limit=50,  # 50 requests per minute
            auth_required=True,
            allowed_origins=["*"],
        ),
        RouteConfig(
            path="/api/{path:.*}",
            method="PUT",
            target_url="http://api:8000/api/{path}",
            timeout=60.0,
            rate_limit=50,
            auth_required=True,
            allowed_origins=["*"],
        ),
        RouteConfig(
            path="/api/{path:.*}",
            method="DELETE",
            target_url="http://api:8000/api/{path}",
            timeout=30.0,
            rate_limit=20,
            auth_required=True,
            allowed_origins=["*"],
        ),
        # Streamlit route removed - using Svelte frontend instead
        # RouteConfig(
        #     path="/",
        #     method="GET",
        #     target_url="http://streamlit:8501/",
        #     timeout=10.0,
        #     rate_limit=1000,
        #     auth_required=False,
        #     allowed_origins=["*"]
        # )
    ]

    return routes


# Gateway factory
async def create_gateway(host: str = "0.0.0.0", port: int = 8080) -> APIGateway:
    """Create and configure API Gateway"""
    gateway = APIGateway(host, port)

    # Add default routes
    routes = create_gateway_config()
    for route in routes:
        gateway.add_route(route)

    await gateway.start()
    return gateway
