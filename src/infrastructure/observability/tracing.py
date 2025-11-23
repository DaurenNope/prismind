"""
Distributed Tracing System for Beyondlines
Provides end-to-end request tracking and performance monitoring
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

# Context variables for trace propagation
trace_context: ContextVar[Optional["Trace"]] = ContextVar("trace_context", default=None)
span_context: ContextVar[Optional["Span"]] = ContextVar("span_context", default=None)

logger = logging.getLogger(__name__)


class SpanKind(Enum):
    """Types of spans"""

    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"


class SpanStatus(Enum):
    """Span status codes"""

    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class SpanEvent:
    """Event within a span"""

    timestamp: float
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "name": self.name,
            "attributes": self.attributes,
        }


@dataclass
class SpanLink:
    """Link to another span"""

    trace_id: str
    span_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """Individual span representing a unit of work"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.OK
    status_message: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    service_name: str = "beyondlines"

    def __post_init__(self):
        if not self.span_id:
            self.span_id = str(uuid.uuid4())

    @property
    def duration(self) -> Optional[float]:
        """Get span duration in milliseconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return None

    def set_tag(self, key: str, value: Any):
        """Set a tag on the span"""
        self.tags[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span"""
        event = SpanEvent(timestamp=time.time(), name=name, attributes=attributes or {})
        self.events.append(event)

    def set_status(self, status: SpanStatus, message: Optional[str] = None):
        """Set span status"""
        self.status = status
        self.status_message = message

    def finish(self, end_time: Optional[float] = None):
        """Finish the span"""
        self.end_time = end_time or time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id,
            "operationName": self.operation_name,
            "serviceName": self.service_name,
            "kind": self.kind.value,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "duration": self.duration,
            "status": self.status.value,
            "statusMessage": self.status_message,
            "tags": self.tags,
            "events": [event.to_dict() for event in self.events],
            "links": [asdict(link) for link in self.links],
        }


@dataclass
class Trace:
    """Trace containing multiple spans"""

    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        """Get trace duration in milliseconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return None

    def add_span(self, span: Span):
        """Add a span to the trace"""
        self.spans.append(span)
        if not self.start_time:
            self.start_time = span.start_time
        if span.end_time and (not self.end_time or span.end_time > self.end_time):
            self.end_time = span.end_time

    def get_root_span(self) -> Optional[Span]:
        """Get the root span of the trace"""
        for span in self.spans:
            if span.parent_span_id is None:
                return span
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            "traceId": self.trace_id,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "duration": self.duration,
            "spanCount": len(self.spans),
            "spans": [span.to_dict() for span in self.spans],
        }


class Tracer:
    """Tracer for creating and managing spans"""

    def __init__(self, service_name: str = "beyondlines"):
        self.service_name = service_name
        self._active_traces: Dict[str, Trace] = {}

    def start_trace(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new trace"""
        trace_id = str(uuid.uuid4())
        span = Span(
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            operation_name=operation_name,
            start_time=time.time(),
            kind=kind,
            service_name=self.service_name,
            tags=tags or {},
        )

        trace = Trace(trace_id=trace_id)
        trace.add_span(span)
        self._active_traces[trace_id] = trace

        trace_context.set(trace)
        span_context.set(span)

        logger.debug(f"Started new trace: {trace_id}, span: {span.span_id}")
        return span

    def start_span(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span: Optional[Span] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span"""
        current_span = parent_span or span_context.get()

        if current_span:
            trace_id = current_span.trace_id
            parent_span_id = current_span.span_id
        else:
            trace_id = str(uuid.uuid4())
            parent_span_id = None
            # Create new trace if none exists
            trace = Trace(trace_id=trace_id)
            self._active_traces[trace_id] = trace

        span = Span(
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            kind=kind,
            service_name=self.service_name,
            tags=tags or {},
        )

        # Add to trace
        if trace_id in self._active_traces:
            self._active_traces[trace_id].add_span(span)

        span_context.set(span)
        logger.debug(f"Started span: {span.span_id}, parent: {parent_span_id}")
        return span

    def finish_span(
        self,
        span: Span,
        status: SpanStatus = SpanStatus.OK,
        message: Optional[str] = None,
    ):
        """Finish a span"""
        span.set_status(status, message)
        span.finish()

        if span.trace_id in self._active_traces:
            self._active_traces[span.trace_id].add_span(span)

        logger.debug(f"Finished span: {span.span_id} with status: {status.value}")

    def get_current_trace(self) -> Optional[Trace]:
        """Get current trace"""
        trace = trace_context.get()
        if trace and trace.trace_id in self._active_traces:
            return self._active_traces[trace.trace_id]
        return None

    def get_current_span(self) -> Optional[Span]:
        """Get current span"""
        return span_context.get()

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get trace by ID"""
        return self._active_traces.get(trace_id)

    def finish_trace(self, trace_id: str):
        """Finish a trace"""
        if trace_id in self._active_traces:
            trace = self._active_traces[trace_id]
            if trace.end_time is None:
                trace.end_time = time.time()
            logger.debug(f"Finished trace: {trace_id}")

    @asynccontextmanager
    async def trace_async(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Async context manager for tracing"""
        span = self.start_span(operation_name, kind, tags=tags)
        try:
            yield span
            self.finish_span(span, SpanStatus.OK)
        except Exception as e:
            logger.error(f"Error: {e}")
            self.finish_span(span, SpanStatus.ERROR, str(e))
            raise

    def trace(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Decorator for tracing functions"""

        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    async with self.trace_async(operation_name, kind, tags):
                        return await func(*args, **kwargs)

                return async_wrapper
            else:

                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    span = self.start_span(operation_name, kind, tags)
                    try:
                        result = func(*args, **kwargs)
                        self.finish_span(span, SpanStatus.OK)
                        return result
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        self.finish_span(span, SpanStatus.ERROR, str(e))
                        raise

                return sync_wrapper

        return decorator


class TraceCollector:
    """Collects and stores traces for analysis"""

    def __init__(self, max_traces: int = 10000):
        self.max_traces = max_traces
        self._traces: Dict[str, Trace] = {}
        self._lock = asyncio.Lock()

    async def collect_trace(self, trace: Trace):
        """Collect a trace"""
        async with self._lock:
            if len(self._traces) >= self.max_traces:
                # Remove oldest traces
                oldest_traces = sorted(
                    self._traces.items(), key=lambda x: x[1].start_time or 0
                )[: len(self._traces) // 2]
                for trace_id, _ in oldest_traces:
                    del self._traces[trace_id]

            self._traces[trace.trace_id] = trace

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID"""
        async with self._lock:
            return self._traces.get(trace_id)

    async def list_traces(
        self,
        limit: int = 100,
        service_name: Optional[str] = None,
        min_duration: Optional[float] = None,
    ) -> List[Trace]:
        """List traces with optional filtering"""
        async with self._lock:
            traces = list(self._traces.values())

            # Apply filters
            if service_name:
                traces = [
                    trace
                    for trace in traces
                    if any(span.service_name == service_name for span in trace.spans)
                ]

            if min_duration is not None:
                traces = [
                    trace
                    for trace in traces
                    if trace.duration and trace.duration >= min_duration
                ]

            # Sort by start time (newest first) and limit
            traces.sort(key=lambda x: x.start_time or 0, reverse=True)
            return traces[:limit]

    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get metrics by service"""
        async with self._lock:
            metrics = {}
            for trace in self._traces.values():
                for span in trace.spans:
                    service = span.service_name
                    if service not in metrics:
                        metrics[service] = {
                            "span_count": 0,
                            "error_count": 0,
                            "total_duration": 0,
                            "avg_duration": 0,
                        }

                    metrics[service]["span_count"] += 1
                    if span.status == SpanStatus.ERROR:
                        metrics[service]["error_count"] += 1
                    if span.duration:
                        metrics[service]["total_duration"] += span.duration

            # Calculate averages
            for service_data in metrics.values():
                if service_data["span_count"] > 0:
                    service_data["avg_duration"] = (
                        service_data["total_duration"] / service_data["span_count"]
                    )

            return metrics


# Global tracer and collector instances
tracer = Tracer()
trace_collector = TraceCollector()


# Auto-instrumentation decorators
def trace_function(
    operation_name: Optional[str] = None, kind: SpanKind = SpanKind.INTERNAL
):
    """Decorator for automatic function tracing"""

    def decorator(func: Callable) -> Callable:
        name = operation_name or f"{func.__module__}.{func.__qualname__}"
        return tracer.trace(name, kind)

    return decorator


def trace_async_function(
    operation_name: Optional[str] = None, kind: SpanKind = SpanKind.INTERNAL
):
    """Decorator for automatic async function tracing"""

    def decorator(func: Callable) -> Callable:
        name = operation_name or f"{func.__module__}.{func.__qualname__}"
        return tracer.trace(name, kind)

    return decorator


# Utility functions
def get_trace_headers() -> Dict[str, str]:
    """Get headers for trace propagation"""
    span = span_context.get()
    if span:
        return {
            "x-trace-id": span.trace_id,
            "x-span-id": span.span_id,
            "x-parent-span-id": span.parent_span_id or "",
        }
    return {}


def set_trace_from_headers(headers: Dict[str, str]):
    """Set trace context from headers"""
    trace_id = headers.get("x-trace-id")
    span_id = headers.get("x-span-id")
    parent_span_id = headers.get("x-parent-span-id")

    if trace_id and span_id:
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name="propagated",
            start_time=time.time(),
            service_name=tracer.service_name,
        )
        span_context.set(span)

        # Reconstruct trace if needed
        if trace_id not in tracer._active_traces:
            trace = Trace(trace_id=trace_id)
            tracer._active_traces[trace_id] = trace
        trace_context.set(tracer._active_traces[trace_id])
