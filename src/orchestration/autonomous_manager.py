"""
Beyondlines Autonomous Manager
Central coordinator for fully autonomous operation
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.config_validator import get_config, is_production
from ..utils.exceptions import (
    BEYONDLINESException,
    ConfigurationError,
    DatabaseError,
    RetryExhaustedError,
)
from ..utils.logging_config import get_logger


class SystemStatus(Enum):
    """System operation status"""

    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class HealthCheck:
    """Health check result"""

    component: str
    status: str  # healthy, unhealthy, warning
    message: str
    metrics: Dict[str, Any]
    timestamp: datetime


class AutonomousManager:
    """Central autonomous operations manager"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.status = SystemStatus.STARTING
        self.start_time = datetime.now()
        self.health_checks = {}
        self.metrics = {
            "uptime_seconds": 0,
            "total_recoveries": 0,
            "failed_recoveries": 0,
            "last_health_check": None,
            "performance_metrics": {},
        }

        # Component managers
        self.components = {}
        self.recovery_strategies = {}
        self.optimization_settings = {}

        # Load configuration
        self.config = self._load_configuration()

    async def start(self):
        """Start autonomous operation"""
        try:
            self.logger.info("🚀 Starting Beyondlines Autonomous Manager...")

            # Validate configuration
            await self._validate_configuration()

            # Initialize components
            await self._initialize_components()

            # Start background tasks
            await self._start_background_tasks()

            self.status = SystemStatus.RUNNING
            self.logger.info("✅ Autonomous Manager started successfully")

            # Main autonomous loop
            await self._run_autonomous_loop()

        except Exception as e:
            self.logger.error(f"❌ Failed to start autonomous manager: {e}")
            self.status = SystemStatus.STOPPED
            raise

    async def stop(self):
        """Stop autonomous operation gracefully"""
        self.logger.info("🛑 Stopping Autonomous Manager...")
        self.status = SystemStatus.STOPPING

        # Stop all background tasks
        await self._stop_background_tasks()

        # Shutdown components
        await self._shutdown_components()

        self.status = SystemStatus.STOPPED
        self.logger.info("✅ Autonomous Manager stopped successfully")

    async def _run_autonomous_loop(self):
        """Main autonomous operation loop"""
        while self.status in [SystemStatus.RUNNING, SystemStatus.DEGRADED]:
            try:
                # Update uptime metrics
                self._update_metrics()

                # Perform health checks
                await self._perform_health_checks()

                # Analyze system performance
                await self._analyze_performance()

                # Execute optimizations
                await self._execute_optimizations()

                # Schedule tasks
                await self._schedule_tasks()

                # Adaptive sleep based on system load
                await self._adaptive_sleep()

            except Exception as e:
                self.logger.error(f"❌ Error in autonomous loop: {e}")
                await self._handle_loop_error(e)

    async def _perform_health_checks(self):
        """Perform comprehensive health checks"""
        try:
            health_checks = await self._check_all_components()

            # Update health status
            for component, check in health_checks.items():
                self.health_checks[component] = check

            # Update overall system health
            overall_health = self._assess_overall_health(health_checks)

            # Handle any unhealthy components
            if overall_health["status"] != "healthy":
                await self._handle_health_issues(health_checks)

            self.metrics["last_health_check"] = datetime.now()
            self.logger.debug(f"Health check completed: {overall_health['status']}")

        except Exception as e:
            self.logger.error(f"❌ Health check failed: {e}")

    async def _check_all_components(self) -> Dict[str, HealthCheck]:
        """Check health of all system components"""
        health_checks = {}

        # Database health
        health_checks["database"] = await self._check_database_health()

        # AI services health
        health_checks["ai_services"] = await self._check_ai_services_health()

        # External APIs health
        health_checks["external_apis"] = await self._check_external_apis_health()

        # Resource usage health
        health_checks["resources"] = await self._check_resources_health()

        # Pipeline health
        health_checks["pipeline"] = await self._check_pipeline_health()

        return health_checks

    async def _check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance"""
        start_time = time.time()

        try:
            from src.services.new_database_manager import NewDatabaseManager

            db = NewDatabaseManager()

            # Test basic connectivity
            test_posts = db.get_posts(limit=1)
            response_time = time.time() - start_time

            # Get database stats
            db_stats = await self._get_database_stats(db)

            metrics = {
                "response_time_ms": round(response_time * 1000, 2),
                "connection_pool_size": getattr(db, "pool_size", 1),
                "total_posts": db_stats.get("total_posts", 0),
                "unanalyzed_posts": db_stats.get("unanalyzed", 0),
            }

            # Determine health status
            if response_time > 5.0:  # 5 seconds
                status = "unhealthy"
                message = f"Database response too slow: {response_time:.2f}s"
            elif response_time > 2.0:  # 2 seconds
                status = "warning"
                message = f"Database response slow: {response_time:.2f}s"
            else:
                status = "healthy"
                message = "Database responding normally"

            return HealthCheck(
                component="database",
                status=status,
                message=message,
                metrics=metrics,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Error: {e}")
            return HealthCheck(
                component="database",
                status="unhealthy",
                message=f"Database connection failed: {str(e)}",
                metrics={"error": str(e)},
                timestamp=datetime.now(),
            )

    async def _check_ai_services_health(self) -> HealthCheck:
        """Check AI service availability and performance"""
        services = {}
        ai_providers = ["openai", "anthropic", "gemini"]

        for provider in ai_providers:
            try:
                api_key = get_config(f"{provider}_api_key")
                if api_key:
                    # Test service availability with a simple request
                    start_time = time.time()
                    test_result = await self._test_ai_service(provider)
                    response_time = time.time() - start_time

                    services[provider] = {
                        "available": True,
                        "response_time_ms": round(response_time * 1000, 2),
                        "test_result": test_result,
                    }
                else:
                    services[provider] = {
                        "available": False,
                        "reason": "API key not configured",
                    }

            except Exception as e:
                logger.error(f"Error: {e}")
                services[provider] = {"available": False, "error": str(e)}

        # Calculate overall status
        available_count = sum(1 for s in services.values() if s.get("available"))
        total_count = len(services)

        if available_count == 0:
            status = "unhealthy"
            message = "No AI services available"
        elif available_count < total_count:
            status = "warning"
            message = f"Only {available_count}/{total_count} AI services available"
        else:
            status = "healthy"
            message = "All AI services available"

        return HealthCheck(
            component="ai_services",
            status=status,
            message=message,
            metrics={"services": services, "available_count": available_count},
            timestamp=datetime.now(),
        )

    async def _check_external_apis_health(self) -> HealthCheck:
        """Check external API connectivity"""
        apis = {}
        external_services = ["twitter", "reddit", "threads"]

        for service in external_services:
            try:
                start_time = time.time()
                # Test basic connectivity
                connectivity = await self._test_external_api(service)
                response_time = time.time() - start_time

                apis[service] = {
                    "connected": connectivity,
                    "response_time_ms": round(response_time * 1000, 2),
                }

            except Exception as e:
                logger.error(f"Error: {e}")
                apis[service] = {"connected": False, "error": str(e)}

        connected_count = sum(1 for a in apis.values() if a.get("connected"))

        if connected_count == 0:
            status = "unhealthy"
            message = "No external APIs accessible"
        elif connected_count < len(external_services):
            status = "warning"
            message = f"Only {connected_count}/{len(external_services)} APIs accessible"
        else:
            status = "healthy"
            message = "All external APIs accessible"

        return HealthCheck(
            component="external_apis",
            status=status,
            message=message,
            metrics={"apis": apis, "connected_count": connected_count},
            timestamp=datetime.now(),
        )

    async def _check_resources_health(self) -> HealthCheck:
        """Check system resource usage"""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / 1024**3, 2),
                "memory_total_gb": round(memory.total / 1024**3, 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / 1024**3, 2),
                "disk_total_gb": round(disk.total / 1024**3, 2),
            }

            # Determine health status
            critical_issues = []
            warnings = []

            if cpu_percent > 90:
                critical_issues.append(f"High CPU usage: {cpu_percent}%")
            elif cpu_percent > 80:
                warnings.append(f"Elevated CPU usage: {cpu_percent}%")

            if memory.percent > 90:
                critical_issues.append(f"High memory usage: {memory.percent}%")
            elif memory.percent > 80:
                warnings.append(f"Elevated memory usage: {memory.percent}%")

            if disk.percent > 95:
                critical_issues.append(f"High disk usage: {disk.percent}%")
            elif disk.percent > 85:
                warnings.append(f"Elevated disk usage: {disk.percent}%")

            if critical_issues:
                status = "unhealthy"
                message = "; ".join(critical_issues)
            elif warnings:
                status = "warning"
                message = "; ".join(warnings)
            else:
                status = "healthy"
                message = "Resource usage normal"

            return HealthCheck(
                component="resources",
                status=status,
                message=message,
                metrics=metrics,
                timestamp=datetime.now(),
            )

        except ImportError:
            logger.error(f"Error: {e}")
            return HealthCheck(
                component="resources",
                status="unknown",
                message="psutil not available for resource monitoring",
                metrics={},
                timestamp=datetime.now(),
            )

    async def _check_pipeline_health(self) -> HealthCheck:
        """Check content pipeline status"""
        try:
            pipeline_metrics = await self._get_pipeline_metrics()

            metrics = {
                "total_processed": pipeline_metrics.get("total_processed", 0),
                "processing_rate_per_hour": pipeline_metrics.get("processing_rate", 0),
                "error_rate": pipeline_metrics.get("error_rate", 0),
                "average_processing_time": pipeline_metrics.get(
                    "avg_processing_time", 0
                ),
                "queue_sizes": pipeline_metrics.get("queue_sizes", {}),
            }

            error_rate = metrics["error_rate"]
            processing_rate = metrics["processing_rate_per_hour"]

            if error_rate > 0.1:  # 10% error rate
                status = "unhealthy"
                message = f"High error rate: {error_rate:.2%}"
            elif error_rate > 0.05:  # 5% error rate
                status = "warning"
                message = f"Elevated error rate: {error_rate:.2%}"
            elif processing_rate < 10:  # Less than 10 items per hour
                status = "warning"
                message = f"Low processing rate: {processing_rate:.1f}/hour"
            else:
                status = "healthy"
                message = "Pipeline operating normally"

            return HealthCheck(
                component="pipeline",
                status=status,
                message=message,
                metrics=metrics,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Error: {e}")
            return HealthCheck(
                component="pipeline",
                status="unhealthy",
                message=f"Pipeline health check failed: {str(e)}",
                metrics={"error": str(e)},
                timestamp=datetime.now(),
            )

    def _assess_overall_health(
        self, health_checks: Dict[str, HealthCheck]
    ) -> Dict[str, Any]:
        """Assess overall system health"""
        statuses = [check.status for check in health_checks.values()]

        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "components": {name: check.status for name, check in health_checks.items()},
            "timestamp": datetime.now().isoformat(),
        }

    async def _handle_health_issues(self, health_checks: Dict[str, HealthCheck]):
        """Handle detected health issues"""
        for component, check in health_checks.items():
            if check.status == "unhealthy":
                self.logger.warning(
                    f"⚠️ Unhealthy component detected: {component} - {check.message}"
                )
                await self._attempt_recovery(component, check)
            elif check.status == "warning":
                self.logger.info(
                    f"⚠️ Warning for component: {component} - {check.message}"
                )

    async def _attempt_recovery(self, component: str, health_check: HealthCheck):
        """Attempt to recover unhealthy component"""
        self.metrics["total_recoveries"] += 1

        try:
            self.logger.info(f"🔄 Attempting recovery for {component}")

            # Implement recovery strategies based on component
            if component == "database":
                await self._recover_database()
            elif component == "ai_services":
                await self._recover_ai_services()
            elif component == "external_apis":
                await self._recover_external_apis()
            elif component == "resources":
                await self._recover_resources()
            elif component == "pipeline":
                await self._recover_pipeline()

            # Verify recovery
            await asyncio.sleep(5)  # Wait for recovery to take effect
            verification = await self._verify_recovery(component)

            if verification:
                self.logger.info(f"✅ Recovery successful for {component}")
            else:
                self.logger.error(f"❌ Recovery failed for {component}")
                self.metrics["failed_recoveries"] += 1

        except Exception as e:
            self.logger.error(f"❌ Recovery attempt failed for {component}: {e}")
            self.metrics["failed_recoveries"] += 1

    async def _load_configuration(self) -> Dict[str, Any]:
        """Load autonomous operation configuration"""
        return {
            "health_check_interval": get_config("health_check_interval", 30),
            "max_retry_attempts": get_config("max_retry_attempts", 5),
            "circuit_breaker_threshold": get_config("circuit_breaker_threshold", 10),
            "optimization_interval": get_config(
                "optimization_interval", 300
            ),  # 5 minutes
            "adaptive_sleep_base": get_config("adaptive_sleep_base", 60),  # 1 minute
            "auto_recovery_enabled": get_config("auto_recovery_enabled", True),
            "performance_optimization": get_config("performance_optimization", True),
        }

    async def _adaptive_sleep(self):
        """Adaptive sleep based on system load and activity"""
        base_sleep = self.config.get("adaptive_sleep_base", 60)

        try:
            # Get current resource usage
            resource_health = self.health_checks.get("resources")
            if resource_health and resource_health.metrics:
                cpu_usage = resource_health.metrics.get("cpu_percent", 0)
                memory_usage = resource_health.metrics.get("memory_percent", 0)

                # Increase sleep time under high load
                load_factor = max(cpu_usage, memory_usage) / 100
                sleep_time = base_sleep * (1 + load_factor)
            else:
                sleep_time = base_sleep

            # Adjust based on system status
            if self.status == SystemStatus.DEGRADED:
                sleep_time *= 0.5  # Check more frequently when degraded

            self.logger.debug(f"Sleeping for {sleep_time:.1f} seconds")
            await asyncio.sleep(sleep_time)

        except Exception as e:
            self.logger.warning(f"Error in adaptive sleep: {e}")
            await asyncio.sleep(base_sleep)

    def _update_metrics(self):
        """Update system metrics"""
        uptime = datetime.now() - self.start_time
        self.metrics["uptime_seconds"] = uptime.total_seconds()
        self.metrics["status"] = self.status.value

    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        return {
            "status": self.status.value,
            "uptime_seconds": self.metrics["uptime_seconds"],
            "start_time": self.start_time.isoformat(),
            "health_checks": {
                name: {
                    "status": check.status,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "metrics": check.metrics,
                }
                for name, check in self.health_checks.items()
            },
            "metrics": self.metrics,
            "configuration": self.config,
        }


# Global autonomous manager instance
autonomous_manager = AutonomousManager()
