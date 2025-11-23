"""
Application Metrics Collection
============================

Collects application-level, database, and business metrics for monitoring.
Integrates with the performance monitor for comprehensive metrics collection.

Author: Prismind Production Team
"""

import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from threading import Lock

from src.monitoring.performance_monitor import get_performance_monitor
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ApplicationMetric:
    """Application-level metric"""

    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class DatabaseMetric:
    """Database operation metric"""

    operation: str
    duration_ms: float
    success: bool
    table: Optional[str] = None
    query_type: Optional[str] = None
    timestamp: datetime = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class BusinessMetric:
    """Business-level metric"""

    metric_name: str
    value: int
    timestamp: datetime
    tags: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """Collects and aggregates metrics"""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self._lock = Lock()

        # Metrics storage
        self.application_metrics: deque = deque(maxlen=max_history)
        self.database_metrics: deque = deque(maxlen=max_history)
        self.business_metrics: deque = deque(maxlen=max_history)

        # Aggregated counters
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)

    def record_application_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "count",
        tags: Optional[Dict[str, str]] = None,
    ):
        """Record an application metric"""
        metric = ApplicationMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            tags=tags or {},
        )

        with self._lock:
            self.application_metrics.append(metric)

    def record_database_metric(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        table: Optional[str] = None,
        query_type: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Record a database operation metric"""
        metric = DatabaseMetric(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            table=table,
            query_type=query_type,
            error=error,
        )

        with self._lock:
            self.database_metrics.append(metric)

        # Also record in performance monitor
        perf_monitor = get_performance_monitor()
        perf_monitor.record_operation(
            operation_name=f"db_{operation}",
            execution_time=duration_ms / 1000.0,
            success=success,
            error_message=error,
            context={"table": table, "query_type": query_type},
        )

    def record_business_metric(
        self,
        metric_name: str,
        value: int,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Record a business metric"""
        metric = BusinessMetric(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
        )

        with self._lock:
            self.business_metrics.append(metric)

    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        key = self._make_key(name, tags)
        with self._lock:
            self.counters[key] += value

        # Also record as application metric
        self.record_application_metric(name, float(value), "count", tags)

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        key = self._make_key(name, tags)
        with self._lock:
            self.gauges[key] = value

        self.record_application_metric(name, value, "gauge", tags)

    def record_histogram(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ):
        """Record a histogram value"""
        key = self._make_key(name, tags)
        with self._lock:
            self.histograms[key].append(value)
            # Keep only recent values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]

    def _make_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """Create a key from metric name and tags"""
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}:{tag_str}"
        return name

    @contextmanager
    def measure_database_operation(
        self,
        operation: str,
        table: Optional[str] = None,
        query_type: Optional[str] = None,
    ):
        """Context manager for measuring database operations"""
        start_time = time.time()
        success = True
        error = None

        try:
            yield
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_database_metric(
                operation=operation,
                duration_ms=duration_ms,
                success=success,
                table=table,
                query_type=query_type,
                error=error,
            )

    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get summary of metrics for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            # Application metrics summary
            recent_app_metrics = [
                m
                for m in self.application_metrics
                if m.timestamp >= cutoff_time
            ]

            # Database metrics summary
            recent_db_metrics = [
                m for m in self.database_metrics if m.timestamp >= cutoff_time
            ]

            # Business metrics summary
            recent_business_metrics = [
                m for m in self.business_metrics if m.timestamp >= cutoff_time
            ]

        # Aggregate database metrics by operation
        db_summary = defaultdict(lambda: {"count": 0, "total_ms": 0, "errors": 0})
        for metric in recent_db_metrics:
            op_key = metric.operation
            db_summary[op_key]["count"] += 1
            db_summary[op_key]["total_ms"] += metric.duration_ms
            if not metric.success:
                db_summary[op_key]["errors"] += 1

        # Calculate averages
        for op_key in db_summary:
            summary = db_summary[op_key]
            if summary["count"] > 0:
                summary["avg_ms"] = summary["total_ms"] / summary["count"]
                summary["error_rate"] = (
                    summary["errors"] / summary["count"] * 100
                    if summary["count"] > 0
                    else 0
                )

        # Aggregate business metrics
        business_summary = defaultdict(int)
        for metric in recent_business_metrics:
            business_summary[metric.metric_name] += metric.value

        return {
            "application_metrics_count": len(recent_app_metrics),
            "database_metrics": dict(db_summary),
            "business_metrics": dict(business_summary),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histogram_summaries": {
                name: {
                    "count": len(values),
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "avg": sum(values) / len(values) if values else 0,
                }
                for name, values in self.histograms.items()
                if values
            },
            "period_hours": hours,
            "generated_at": datetime.now().isoformat(),
        }

    def get_database_performance(self, hours: int = 1) -> Dict[str, Any]:
        """Get database performance metrics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_metrics = [
                m for m in self.database_metrics if m.timestamp >= cutoff_time
            ]

        if not recent_metrics:
            return {"message": "No database metrics in the specified period"}

        # Group by table and operation
        by_table = defaultdict(lambda: {"operations": defaultdict(list), "total": 0})
        by_operation = defaultdict(list)

        for metric in recent_metrics:
            if metric.table:
                by_table[metric.table]["operations"][metric.operation].append(metric)
                by_table[metric.table]["total"] += 1
            by_operation[metric.operation].append(metric)

        # Calculate statistics
        table_stats = {}
        for table, data in by_table.items():
            all_durations = []
            errors = 0
            for ops in data["operations"].values():
                for metric in ops:
                    all_durations.append(metric.duration_ms)
                    if not metric.success:
                        errors += 1

            if all_durations:
                table_stats[table] = {
                    "operation_count": data["total"],
                    "avg_duration_ms": sum(all_durations) / len(all_durations),
                    "min_duration_ms": min(all_durations),
                    "max_duration_ms": max(all_durations),
                    "error_count": errors,
                    "error_rate": (errors / len(all_durations)) * 100,
                }

        operation_stats = {}
        for operation, metrics in by_operation.items():
            durations = [m.duration_ms for m in metrics]
            errors = sum(1 for m in metrics if not m.success)

            operation_stats[operation] = {
                "count": len(metrics),
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "error_count": errors,
                "error_rate": (errors / len(metrics)) * 100 if metrics else 0,
            }

        return {
            "period_hours": hours,
            "total_operations": len(recent_metrics),
            "by_table": table_stats,
            "by_operation": operation_stats,
            "generated_at": datetime.now().isoformat(),
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector






