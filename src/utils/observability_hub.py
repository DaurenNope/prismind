#!/usr/bin/env python3
"""
Observability Hub for BEYONDLINES
================================

Unified observability layer providing:
- Structured logging with correlation IDs
- Distributed tracing across services
- Metrics collection (Prometheus-style)
- Error tracking and aggregation

Author: BEYONDLINES AI System
"""

import time
import uuid
from collections import defaultdict, deque
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from src.infrastructure.observability.tracing import (
    Span,
    SpanKind,
    SpanStatus,
    Tracer,
    span_context,
    trace_context,
)
from src.shared.utils.logging_config import get_logger, get_performance_logger


class MetricType(Enum):
    """Types of metrics"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """A metric measurement"""

    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


@dataclass
class ErrorReport:
    """An error report for tracking"""

    error_type: str
    message: str
    traceback: Optional[str]
    context: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "traceback": self.traceback,
            "context": self.context,
            "timestamp": self.timestamp,
            "count": self.count,
        }


class MetricsCollector:
    """Collects and aggregates metrics"""

    def __init__(self, max_samples: int = 1000):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_samples)
        )
        self._summaries: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_samples)
        )
        self._metrics_history: List[Metric] = []
        self.logger = get_logger(__name__)

    def increment(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ):
        """Increment a counter metric"""
        key = self._make_key(name, labels)
        self._counters[key] += value
        self._record_metric(name, value, MetricType.COUNTER, labels or {})

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Set a gauge metric"""
        key = self._make_key(name, labels)
        self._gauges[key] = value
        self._record_metric(name, value, MetricType.GAUGE, labels or {})

    def record_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Record a histogram value"""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        self._record_metric(name, value, MetricType.HISTOGRAM, labels or {})

    def record_summary(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Record a summary value"""
        key = self._make_key(name, labels)
        self._summaries[key].append(value)
        self._record_metric(name, value, MetricType.SUMMARY, labels or {})

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a key for metric storage"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _record_metric(
        self, name: str, value: float, metric_type: MetricType, labels: Dict[str, str]
    ):
        """Record a metric in history"""
        metric = Metric(name=name, value=value, metric_type=metric_type, labels=labels)
        self._metrics_history.append(metric)
        # Keep only recent metrics (last 1000)
        if len(self._metrics_history) > 1000:
            self._metrics_history = self._metrics_history[-1000:]

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value"""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value"""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0.0)

    def get_histogram_stats(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._make_key(name, labels)
        if key not in self._histograms:
            return {}
        values = list(self._histograms[key])
        if not values:
            return {}
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }

    def get_summary_stats(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """Get summary statistics"""
        key = self._make_key(name, labels)
        if key not in self._summaries:
            return {}
        values = list(self._summaries[key])
        if not values:
            return {}
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus format"""
        metrics = {}

        # Copy keys to avoid "dictionary changed size during iteration" error
        # Counters
        counter_keys = list(self._counters.keys())
        for key in counter_keys:
            value = self._counters.get(key, 0.0)
            if value is not None:
                metrics[key] = {"type": "counter", "value": value}

        # Gauges
        gauge_keys = list(self._gauges.keys())
        for key in gauge_keys:
            value = self._gauges.get(key, 0.0)
            if value is not None:
                metrics[key] = {"type": "gauge", "value": value}

        # Histograms - copy keys first to avoid concurrent modification
        histogram_keys = list(self._histograms.keys())
        for key in histogram_keys:
            try:
                # Extract base name (before {labels})
                base_name = key.split("{")[0]
                stats = self.get_histogram_stats(base_name)
                if stats:
                    metrics[key] = {"type": "histogram", "stats": stats}
            except (KeyError, ValueError):
                # Key might have been removed, skip it
                continue

        # Summaries - copy keys first to avoid concurrent modification
        summary_keys = list(self._summaries.keys())
        for key in summary_keys:
            try:
                # Extract base name (before {labels})
                base_name = key.split("{")[0]
                stats = self.get_summary_stats(base_name)
                if stats:
                    metrics[key] = {"type": "summary", "stats": stats}
            except (KeyError, ValueError):
                # Key might have been removed, skip it
                continue

        return metrics

    def reset(self):
        """Reset all metrics"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._summaries.clear()
        self._metrics_history.clear()


class ErrorTracker:
    """Tracks and aggregates errors"""

    def __init__(self, max_errors: int = 1000):
        self._errors: Dict[str, ErrorReport] = {}
        self._error_history: List[ErrorReport] = []
        self._max_errors = max_errors
        self.logger = get_logger(__name__)

    def capture_exception(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ):
        """Capture an exception"""
        import traceback

        error_type = type(exception).__name__
        message = str(exception)
        tb = traceback.format_exc()

        # Create error signature (group similar errors)
        error_key = f"{error_type}:{message[:100]}"

        if error_key in self._errors:
            # Increment count for existing error
            self._errors[error_key].count += 1
        else:
            # Create new error report
            error_report = ErrorReport(
                error_type=error_type,
                message=message,
                traceback=tb,
                context=context or {},
            )
            self._errors[error_key] = error_report
            self._error_history.append(error_report)

            # Trim history if too long
            if len(self._error_history) > self._max_errors:
                old_key = (
                    self._error_history[0].error_type
                    + ":"
                    + self._error_history[0].message[:100]
                )
                if old_key in self._errors:
                    del self._errors[old_key]
                self._error_history = self._error_history[1:]

        # Log the error
        self.logger.error(
            f"Error captured: {error_type}: {message}", context=context or {}
        )

    def get_errors(self, limit: int = 100) -> List[ErrorReport]:
        """Get recent errors"""
        # Copy values to avoid "dictionary changed size during iteration" error
        error_values = list(self._errors.values())
        return sorted(error_values, key=lambda e: e.count, reverse=True)[:limit]

    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics"""
        # Copy items to avoid "dictionary changed size during iteration" error
        error_items = list(self._errors.items())

        total_errors = sum(e.count for _, e in error_items)
        unique_errors = len(error_items)
        error_types = defaultdict(int)
        for _, error in error_items:
            error_types[error.error_type] += error.count

        return {
            "total_errors": total_errors,
            "unique_errors": unique_errors,
            "error_types": dict(error_types),
            "top_errors": [e.to_dict() for e in self.get_errors(10)],
        }

    def reset(self):
        """Reset error tracking"""
        self._errors.clear()
        self._error_history.clear()


class ObservabilityHub:
    """
    Unified observability hub providing logging, tracing, metrics, and error tracking.
    """

    def __init__(self, service_name: str = "beyondlines"):
        self.service_name = service_name
        self.logger = get_logger(__name__)
        self.perf_logger = get_performance_logger()
        self.tracer = Tracer(service_name=service_name)
        self.metrics = MetricsCollector()
        self.errors = ErrorTracker()
        self._correlation_id: ContextVar[Optional[str]] = ContextVar(
            "correlation_id", default=None
        )

    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID"""
        return self._correlation_id.get()

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracing"""
        self._correlation_id.set(correlation_id)

    def generate_correlation_id(self) -> str:
        """Generate and set a new correlation ID"""
        corr_id = str(uuid.uuid4())
        self.set_correlation_id(corr_id)
        return corr_id

    def instrument_function(
        self,
        operation_name: Optional[str] = None,
        track_metrics: bool = True,
        track_errors: bool = True,
        track_trace: bool = True,
    ):
        """
        Decorator to automatically instrument a function with logging, tracing, metrics, and error tracking.

        Args:
            operation_name: Name for the operation (defaults to function name)
            track_metrics: Whether to track metrics
            track_errors: Whether to track errors
            track_trace: Whether to create a trace span
        """

        def decorator(func: Callable) -> Callable:
            op_name = operation_name or func.__name__

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._instrument_execute_async(
                    func,
                    op_name,
                    args,
                    kwargs,
                    track_metrics,
                    track_errors,
                    track_trace,
                )

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._instrument_execute(
                    func,
                    op_name,
                    args,
                    kwargs,
                    track_metrics,
                    track_errors,
                    track_trace,
                )

            # Return appropriate wrapper based on function type
            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    async def _instrument_execute_async(
        self,
        func: Callable,
        operation_name: str,
        args: tuple,
        kwargs: dict,
        track_metrics: bool,
        track_errors: bool,
        track_trace: bool,
    ):
        """Execute async function with instrumentation"""
        start_time = time.time()

        # Generate correlation ID if not set
        corr_id = self.get_correlation_id() or self.generate_correlation_id()

        # Create trace span if requested
        span = None
        if track_trace:
            span = self.tracer.start_span(
                operation_name=operation_name,
                kind=SpanKind.INTERNAL,
                tags={
                    "correlation_id": corr_id,
                    "function": func.__name__,
                    "module": func.__module__,
                },
            )
            span_context.set(span)

        # Increment call counter
        if track_metrics:
            self.metrics.increment(
                f"{operation_name}.called", labels={"correlation_id": corr_id}
            )

        try:
            # Execute async function
            result = await func(*args, **kwargs)

            # Record success
            duration = time.time() - start_time
            if track_metrics:
                self.metrics.increment(
                    f"{operation_name}.success", labels={"correlation_id": corr_id}
                )
                self.metrics.record_histogram(
                    f"{operation_name}.duration",
                    duration,
                    labels={"correlation_id": corr_id},
                )

            if span:
                span.set_status(SpanStatus.OK)
                span.finish()

            return result

        except Exception as e:
            logger.error(f"Error: {e}")
            # Record error
            duration = time.time() - start_time
            error_type = type(e).__name__

            if track_metrics:
                self.metrics.increment(
                    f"{operation_name}.error",
                    labels={"correlation_id": corr_id, "error_type": error_type},
                )
                self.metrics.record_histogram(
                    f"{operation_name}.duration",
                    duration,
                    labels={"correlation_id": corr_id, "error": "true"},
                )

            if track_errors:
                self.errors.capture_exception(
                    e,
                    context={
                        "correlation_id": corr_id,
                        "operation": operation_name,
                        "function": func.__name__,
                        "module": func.__module__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    },
                )

            if span:
                span.set_status(SpanStatus.ERROR, message=str(e))
                span.add_event("error", {"error_type": error_type, "message": str(e)})
                span.finish()

            raise

    def _instrument_execute(
        self,
        func: Callable,
        operation_name: str,
        args: tuple,
        kwargs: dict,
        track_metrics: bool,
        track_errors: bool,
        track_trace: bool,
    ):
        """Execute sync function with instrumentation"""
        start_time = time.time()

        # Generate correlation ID if not set
        corr_id = self.get_correlation_id() or self.generate_correlation_id()

        # Create trace span if requested
        span = None
        if track_trace:
            span = self.tracer.start_span(
                operation_name=operation_name,
                kind=SpanKind.INTERNAL,
                tags={
                    "correlation_id": corr_id,
                    "function": func.__name__,
                    "module": func.__module__,
                },
            )
            span_context.set(span)

        # Increment call counter
        if track_metrics:
            self.metrics.increment(
                f"{operation_name}.called", labels={"correlation_id": corr_id}
            )

        try:
            # Execute sync function
            result = func(*args, **kwargs)

            # Record success
            duration = time.time() - start_time
            if track_metrics:
                self.metrics.increment(
                    f"{operation_name}.success", labels={"correlation_id": corr_id}
                )
                self.metrics.record_histogram(
                    f"{operation_name}.duration",
                    duration,
                    labels={"correlation_id": corr_id},
                )

            if span:
                span.set_status(SpanStatus.OK)
                span.finish()

            return result

        except Exception as e:
            logger.error(f"Error: {e}")
            # Record error
            duration = time.time() - start_time
            error_type = type(e).__name__

            if track_metrics:
                self.metrics.increment(
                    f"{operation_name}.error",
                    labels={"correlation_id": corr_id, "error_type": error_type},
                )
                self.metrics.record_histogram(
                    f"{operation_name}.duration",
                    duration,
                    labels={"correlation_id": corr_id, "error": "true"},
                )

            if track_errors:
                self.errors.capture_exception(
                    e,
                    context={
                        "correlation_id": corr_id,
                        "operation": operation_name,
                        "function": func.__name__,
                        "module": func.__module__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    },
                )

            if span:
                span.set_status(SpanStatus.ERROR, message=str(e))
                span.add_event("error", {"error_type": error_type, "message": str(e)})
                span.finish()

            raise

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        error_summary = self.errors.get_error_summary()
        metrics_summary = self.metrics.get_all_metrics()

        return {
            "service": self.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self.get_correlation_id(),
            "metrics": {
                "total_metrics": len(metrics_summary),
                "summary": metrics_summary,
            },
            "errors": error_summary,
            "traces": {"active_traces": len(self.tracer._active_traces)},
        }

    def reset(self):
        """Reset all observability data"""
        self.metrics.reset()
        self.errors.reset()
        self.tracer._active_traces.clear()


# Global instance
_observability_hub: Optional[ObservabilityHub] = None


def get_observability_hub(service_name: str = "beyondlines") -> ObservabilityHub:
    """Get or create the global observability hub"""
    global _observability_hub
    if _observability_hub is None:
        _observability_hub = ObservabilityHub(service_name=service_name)
    return _observability_hub


def instrument_function(operation_name: Optional[str] = None, **kwargs):
    """Convenience decorator for function instrumentation"""
    hub = get_observability_hub()
    return hub.instrument_function(operation_name=operation_name, **kwargs)
