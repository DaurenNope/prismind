"""
BEYONDLINES Performance Monitoring System
====================================

Comprehensive performance monitoring for the BEYONDLINES application.
Tracks system metrics, API response times, resource usage, and alerting.

Author: BEYONDLINES AI System
"""

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import psutil

from src.shared.utils.error_handler import handle_errors
from src.shared.utils.logging_config import get_logger, get_performance_logger

logger = get_logger("performance_monitor")
perf_logger = get_performance_logger()


@dataclass
class SystemMetrics:
    """System-level performance metrics"""

    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class APIMetrics:
    """API performance metrics"""

    endpoint: str
    method: str
    response_time: float
    status_code: int
    timestamp: datetime
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class OperationMetrics:
    """Operation-level performance metrics"""

    operation_name: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """Collects and manages performance metrics"""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history

        # Metrics storage
        self.system_metrics = deque(maxlen=max_history)
        self.api_metrics = deque(maxlen=max_history)
        self.operation_metrics = deque(maxlen=max_history)

        # Aggregated data
        self.hourly_stats = defaultdict(list)
        self.daily_stats = defaultdict(list)

        # Collection lock
        self._lock = threading.Lock()

    @handle_errors
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_usage_percent = disk.percent

        # Network I/O
        network = psutil.net_io_counters()
        network_io = {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv,
        }

        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            disk_usage_percent=disk_usage_percent,
            network_io=network_io,
            timestamp=datetime.now(),
        )

        with self._lock:
            self.system_metrics.append(metrics)

        return metrics

    @handle_errors
    def record_api_metric(self, metric: APIMetrics):
        """Record an API performance metric"""
        with self._lock:
            self.api_metrics.append(metric)

            # Add to hourly stats
            hour_key = metric.timestamp.strftime("%Y-%m-%d %H:00")
            self.hourly_stats[hour_key].append(metric)

            # Add to daily stats
            day_key = metric.timestamp.strftime("%Y-%m-%d")
            self.daily_stats[day_key].append(metric)

    @handle_errors
    def record_operation_metric(self, metric: OperationMetrics):
        """Record an operation performance metric"""
        with self._lock:
            self.operation_metrics.append(metric)

    def get_recent_system_metrics(self, minutes: int = 5) -> List[SystemMetrics]:
        """Get recent system metrics"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        with self._lock:
            return [m for m in self.system_metrics if m.timestamp >= cutoff_time]

    def get_api_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get API performance summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_metrics = [m for m in self.api_metrics if m.timestamp >= cutoff_time]

        if not recent_metrics:
            return {}

        # Group by endpoint
        by_endpoint = defaultdict(list)
        for metric in recent_metrics:
            key = f"{metric.method} {metric.endpoint}"
            by_endpoint[key].append(metric)

        # Calculate statistics
        summary = {}
        for endpoint, metrics in by_endpoint.items():
            response_times = [m.response_time for m in metrics]
            success_count = sum(1 for m in metrics if 200 <= m.status_code < 400)

            summary[endpoint] = {
                "request_count": len(metrics),
                "avg_response_time": sum(response_times) / len(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "success_rate": (success_count / len(metrics)) * 100,
                "error_rate": ((len(metrics) - success_count) / len(metrics)) * 100,
            }

        return summary

    def get_operation_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get operation performance summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_metrics = [
                m for m in self.operation_metrics if m.timestamp >= cutoff_time
            ]

        if not recent_metrics:
            return {}

        # Group by operation name
        by_operation = defaultdict(list)
        for metric in recent_metrics:
            by_operation[metric.operation_name].append(metric)

        # Calculate statistics
        summary = {}
        for operation, metrics in by_operation.items():
            execution_times = [m.execution_time for m in metrics]
            success_count = sum(1 for m in metrics if m.success)

            summary[operation] = {
                "execution_count": len(metrics),
                "avg_execution_time": sum(execution_times) / len(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "success_rate": (success_count / len(metrics)) * 100,
                "error_rate": ((len(metrics) - success_count) / len(metrics)) * 100,
            }

        return summary


class AlertManager:
    """Manages performance alerts and notifications"""

    def __init__(self):
        self.alert_rules = []
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.notification_handlers = []

    def add_alert_rule(self, rule: Dict[str, Any]):
        """Add an alert rule"""
        required_fields = ["name", "metric_type", "threshold", "operator"]
        for field in required_fields:
            if field not in rule:
                raise ValueError(f"Alert rule missing required field: {field}")

        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule['name']}")

    def add_notification_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add a notification handler"""
        self.notification_handlers.append(handler)

    @handle_errors
    def check_alerts(self, metrics_collector: MetricsCollector):
        """Check all alert rules against current metrics"""
        for rule in self.alert_rules:
            alert = self._evaluate_rule(rule, metrics_collector)

            if alert:
                alert_key = f"{rule['name']}_{rule['metric_type']}"

                if alert_key not in self.active_alerts:
                    # New alert
                    self.active_alerts[alert_key] = alert
                    self.alert_history.append(alert)

                    # Send notifications
                    for handler in self.notification_handlers:
                        try:
                            handler(alert)
                        except Exception as e:
                            logger.error(f"Notification handler failed: {e}")

                    logger.warning(f"Alert triggered: {alert['title']}")

            else:
                # Clear resolved alerts
                alert_key = f"{rule['name']}_{rule['metric_type']}"
                if alert_key in self.active_alerts:
                    del self.active_alerts[alert_key]
                    logger.info(f"Alert resolved: {rule['name']}")

    def _evaluate_rule(
        self, rule: Dict[str, Any], collector: MetricsCollector
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single alert rule"""
        metric_type = rule["metric_type"]
        threshold = rule["threshold"]
        operator = rule["operator"]

        # Get current metric value
        current_value = None

        if metric_type == "cpu_percent":
            recent_metrics = collector.get_recent_system_metrics(minutes=1)
            if recent_metrics:
                current_value = recent_metrics[-1].cpu_percent

        elif metric_type == "memory_percent":
            recent_metrics = collector.get_recent_system_metrics(minutes=1)
            if recent_metrics:
                current_value = recent_metrics[-1].memory_percent

        elif metric_type == "disk_usage_percent":
            recent_metrics = collector.get_recent_system_metrics(minutes=1)
            if recent_metrics:
                current_value = recent_metrics[-1].disk_usage_percent

        elif metric_type == "api_response_time":
            api_summary = collector.get_api_performance_summary(hours=1)
            if api_summary:
                # Use the slowest endpoint
                slowest_endpoint = max(
                    api_summary.items(), key=lambda x: x[1]["avg_response_time"]
                )
                current_value = slowest_endpoint[1]["avg_response_time"]

        elif metric_type == "error_rate":
            api_summary = collector.get_api_performance_summary(hours=1)
            if api_summary:
                # Use the highest error rate
                highest_error = max(
                    api_summary.items(), key=lambda x: x[1]["error_rate"]
                )
                current_value = highest_error[1]["error_rate"]

        if current_value is None:
            return None

        # Check threshold
        triggered = False

        if operator == "greater_than":
            triggered = current_value > threshold
        elif operator == "less_than":
            triggered = current_value < threshold
        elif operator == "equals":
            triggered = current_value == threshold
        elif operator == "greater_than_or_equal":
            triggered = current_value >= threshold
        elif operator == "less_than_or_equal":
            triggered = current_value <= threshold

        if triggered:
            return {
                "title": f"{rule['name']} - {metric_type}",
                "message": f"{metric_type} is {current_value:.2f} (threshold: {threshold})",
                "severity": rule.get("severity", "warning"),
                "metric_type": metric_type,
                "current_value": current_value,
                "threshold": threshold,
                "timestamp": datetime.now().isoformat(),
            }

        return None


class PerformanceMonitor:
    """Main performance monitoring system"""

    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()

        # Monitoring state
        self._running = False
        self._monitor_thread = None
        self._stop_event = threading.Event()

        # Setup default alert rules
        self._setup_default_alerts()

    def _setup_default_alerts(self):
        """Setup default alert rules"""
        default_rules = [
            {
                "name": "High CPU Usage",
                "metric_type": "cpu_percent",
                "threshold": 80.0,
                "operator": "greater_than",
                "severity": "warning",
            },
            {
                "name": "High Memory Usage",
                "metric_type": "memory_percent",
                "threshold": 85.0,
                "operator": "greater_than",
                "severity": "warning",
            },
            {
                "name": "Low Disk Space",
                "metric_type": "disk_usage_percent",
                "threshold": 90.0,
                "operator": "greater_than",
                "severity": "critical",
            },
            {
                "name": "Slow API Response",
                "metric_type": "api_response_time",
                "threshold": 5.0,
                "operator": "greater_than",
                "severity": "warning",
            },
            {
                "name": "High Error Rate",
                "metric_type": "error_rate",
                "threshold": 10.0,
                "operator": "greater_than",
                "severity": "critical",
            },
        ]

        for rule in default_rules:
            self.alert_manager.add_alert_rule(rule)

    @handle_errors
    def start_monitoring(self):
        """Start the performance monitoring loop"""
        if self._running:
            logger.warning("Performance monitoring is already running")
            return

        self._running = True
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self._monitor_thread.start()

        logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop the performance monitoring loop"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running and not self._stop_event.is_set():
            try:
                # Collect system metrics
                self.metrics_collector.collect_system_metrics()

                # Check alerts
                self.alert_manager.check_alerts(self.metrics_collector)

                # Wait for next collection
                self._stop_event.wait(self.collection_interval)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                self._stop_event.wait(5)  # Brief pause on error

    def record_api_call(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        user_agent: str = None,
        ip_address: str = None,
    ):
        """Record an API call for monitoring"""
        metric = APIMetrics(
            endpoint=endpoint,
            method=method,
            response_time=response_time,
            status_code=status_code,
            timestamp=datetime.now(),
            user_agent=user_agent,
            ip_address=ip_address,
        )

        self.metrics_collector.record_api_metric(metric)

    def record_operation(
        self,
        operation_name: str,
        execution_time: float,
        success: bool = True,
        error_message: str = None,
        context: Dict[str, Any] = None,
    ):
        """Record an operation for monitoring"""
        metric = OperationMetrics(
            operation_name=operation_name,
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            context=context,
            timestamp=datetime.now(),
        )

        self.metrics_collector.record_operation_metric(metric)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "system_metrics": [
                m.to_dict()
                for m in self.metrics_collector.get_recent_system_metrics(minutes=5)
            ],
            "api_performance": self.metrics_collector.get_api_performance_summary(
                hours=1
            ),
            "operation_performance": self.metrics_collector.get_operation_performance_summary(
                hours=1
            ),
            "active_alerts": list(self.alert_manager.active_alerts.values()),
            "system_status": self._get_system_status(),
        }

    def _get_system_status(self) -> str:
        """Get overall system status"""
        recent_metrics = self.metrics_collector.get_recent_system_metrics(minutes=5)

        if not recent_metrics:
            return "unknown"

        latest = recent_metrics[-1]

        # Check for critical issues
        if (
            latest.cpu_percent > 90
            or latest.memory_percent > 95
            or latest.disk_usage_percent > 95
        ):
            return "critical"

        # Check for warnings
        if (
            latest.cpu_percent > 80
            or latest.memory_percent > 85
            or latest.disk_usage_percent > 90
        ):
            return "warning"

        return "healthy"

    def export_metrics(self, filepath: str):
        """Export metrics to a JSON file"""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "system_metrics": [
                m.to_dict() for m in self.metrics_collector.system_metrics
            ],
            "api_metrics": [m.to_dict() for m in self.metrics_collector.api_metrics],
            "operation_metrics": [
                m.to_dict() for m in self.metrics_collector.operation_metrics
            ],
            "active_alerts": list(self.alert_manager.active_alerts.values()),
            "alert_history": list(self.alert_manager.alert_history),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Metrics exported to {filepath}")


# Global instance
_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def monitor_performance(operation_name: str = None):
    """Decorator for automatic performance monitoring"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Error: {e}")
                success = False
                error_message = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                name = operation_name or func.__name__

                monitor = get_performance_monitor()
                monitor.record_operation(
                    operation_name=name,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message,
                )

        return wrapper

    return decorator
