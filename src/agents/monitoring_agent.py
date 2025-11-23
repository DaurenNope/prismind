#!/usr/bin/env python3
"""
Monitoring Agent

Centralized system health monitoring, performance metrics collection, and alerting.
Inherits from BaseAgent and provides comprehensive observability for the system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import smtplib
import time
from collections import deque
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import psutil
import yaml

from src.domain.intelligence.agents.base_agent import AgentError, AgentStatus, BaseAgent
from src.domain.intelligence.agents.registry import get_registry
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class AlertChannel:
    """Alert channel configuration"""

    def __init__(self, channel_type: str, config: Dict[str, Any]):
        self.channel_type = channel_type
        self.config = config
        self.enabled = config.get("enabled", False)

    async def send_alert(
        self, level: str, title: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an alert through this channel.

        Args:
            level: Alert level (info, warning, critical)
            title: Alert title
            message: Alert message
            metadata: Optional metadata

        Returns:
            True if alert was sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            if self.channel_type == "email":
                return await self._send_email(level, title, message, metadata)
            elif self.channel_type == "slack":
                return await self._send_slack(level, title, message, metadata)
            elif self.channel_type == "telegram":
                return await self._send_telegram(level, title, message, metadata)
            else:
                logger.warning(f"Unknown alert channel type: {self.channel_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to send alert via {self.channel_type}: {e}", exc_info=True)
            return False

    async def _send_email(
        self, level: str, title: str, message: str, metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Send alert via email"""
        try:
            smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
            smtp_port = self.config.get("smtp_port", 587)
            smtp_user = self.config.get("smtp_user")
            smtp_password = self.config.get("smtp_password")
            to_email = self.config.get("to_email")

            if not all([smtp_user, smtp_password, to_email]):
                logger.warning("Email alert channel not fully configured")
                return False

            msg = MIMEText(f"{title}\n\n{message}\n\nMetadata: {json.dumps(metadata or {}, indent=2)}")
            msg["Subject"] = f"[{level.upper()}] {title}"
            msg["From"] = smtp_user
            msg["To"] = to_email

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info(f"Alert sent via email: {title}")
            return True
        except Exception as e:
            logger.error(f"Email alert failed: {e}", exc_info=True)
            return False

    async def _send_slack(
        self, level: str, title: str, message: str, metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Send alert via Slack webhook"""
        try:
            webhook_url = self.config.get("webhook_url")
            if not webhook_url:
                logger.warning("Slack webhook URL not configured")
                return False

            color_map = {"info": "#36a64f", "warning": "#ff9900", "critical": "#ff0000"}
            color = color_map.get(level, "#36a64f")

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": title,
                        "text": message,
                        "fields": [
                            {"title": "Level", "value": level.upper(), "short": True},
                            {
                                "title": "Timestamp",
                                "value": datetime.now().isoformat(),
                                "short": True,
                            },
                        ],
                        "footer": "BEYONDLINES Monitoring",
                        "ts": int(time.time()),
                    }
                ]
            }

            if metadata:
                payload["attachments"][0]["fields"].extend(
                    [{"title": k, "value": str(v), "short": True} for k, v in metadata.items()]
                )

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10.0)
                response.raise_for_status()

            logger.info(f"Alert sent via Slack: {title}")
            return True
        except Exception as e:
            logger.error(f"Slack alert failed: {e}", exc_info=True)
            return False

    async def _send_telegram(
        self, level: str, title: str, message: str, metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Send alert via Telegram"""
        try:
            bot_token = self.config.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = self.config.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID")

            if not bot_token or not chat_id:
                logger.warning("Telegram credentials not configured")
                return False

            emoji_map = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}
            emoji = emoji_map.get(level, "ℹ️")

            text = f"{emoji} <b>{title}</b>\n\n{message}"
            if metadata:
                text += "\n\n<b>Details:</b>\n"
                for k, v in metadata.items():
                    text += f"• {k}: {v}\n"

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()

            logger.info(f"Alert sent via Telegram: {title}")
            return True
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}", exc_info=True)
            return False


class MonitoringAgent(BaseAgent):
    """
    Monitoring Agent for system health, performance metrics, and alerting.

    Features:
    - System health monitoring (agents, services, resources)
    - Performance metrics collection
    - Alerting with multiple channels
    - Dashboard data aggregation
    """

    def __init__(
        self,
        agent_id: str = "monitoring_agent",
        agent_name: str = "Monitoring Agent",
        agent_version: str = "1.0.0",
        config_path: Optional[str] = None,
    ):
        """
        Initialize the Monitoring Agent.

        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name
            agent_version: Version string
            config_path: Path to configuration file
        """
        super().__init__(agent_id, agent_name, agent_version, dependencies=[])

        # Load configuration
        self.config_path = config_path or "src/agents/config/monitoring_agent.yaml"
        self.config: Dict[str, Any] = {}
        self._load_config()

        # Initialize alert channels
        self.alert_channels: List[AlertChannel] = []
        self._setup_alert_channels()

        # Metrics storage
        self.metrics_history: Dict[str, deque] = {
            "agent_health": deque(maxlen=1000),
            "service_health": deque(maxlen=1000),
            "system_resources": deque(maxlen=1000),
            "performance": deque(maxlen=1000),
            "alerts": deque(maxlen=500),
        }

        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = self.config.get("monitoring_interval_seconds", 60)
        self._health_check_interval = self.config.get("health_check_interval_seconds", 30)
        self._last_agent_check: Dict[str, float] = {}
        self._last_service_check: Dict[str, float] = {}
        self._alert_thresholds = self.config.get("alert_thresholds", {})
        self._alert_cooldown: Dict[str, float] = {}  # Track last alert time per key
        self._last_health_check: Optional[float] = None  # Track last health check time

        # Registry reference
        self.registry = get_registry()

        # Service connections (lazy initialization)
        self._supabase_manager = None
        self._redis_client = None

        logger.info(f"Monitoring Agent initialized (ID: {self.agent_id})")

    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, "r") as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                logger.warning(f"Config file not found: {config_file}, using defaults")
                self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults", exc_info=True)
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "monitoring_interval_seconds": 60,
            "health_check_interval_seconds": 30,
            "alert_thresholds": {
                "cpu_percent": 80.0,
                "memory_percent": 80.0,
                "disk_percent": 90.0,
                "agent_failure_count": 3,
                "service_failure_count": 3,
                "response_time_ms": 1000.0,
            },
            "alert_cooldown_seconds": 300,  # 5 minutes
            "alert_channels": {
                "email": {"enabled": False},
                "slack": {"enabled": False},
                "telegram": {"enabled": False},
            },
        }

    def _setup_alert_channels(self) -> None:
        """Setup alert channels from configuration"""
        channels_config = self.config.get("alert_channels", {})
        for channel_type, channel_config in channels_config.items():
            channel = AlertChannel(channel_type, channel_config)
            if channel.enabled:
                self.alert_channels.append(channel)
                logger.info(f"Alert channel enabled: {channel_type}")

    async def initialize(self) -> bool:
        """
        Initialize the monitoring agent.

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing Monitoring Agent...")

            # Initialize service connections
            await self._initialize_services()

            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

            self._mark_initialized()
            self._set_status(AgentStatus.IDLE)

            logger.info("Monitoring Agent initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Monitoring Agent: {e}", exc_info=True)
            self._set_status(AgentStatus.ERROR)
            return False

    async def _initialize_services(self) -> None:
        """Initialize service connections for monitoring"""
        # Supabase
        try:
            from src.infrastructure.database.manager import SupabaseManager

            self._supabase_manager = SupabaseManager()
            logger.info("Supabase connection initialized for monitoring")
        except Exception as e:
            logger.warning(f"Supabase initialization failed (optional): {e}")

        # Redis (if available)
        try:
            import redis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            self._redis_client.ping()
            logger.info("Redis connection initialized for monitoring")
        except Exception as e:
            logger.debug(f"Redis not available (optional): {e}")

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a monitoring task.

        Args:
            task: Task dictionary with 'action' and optional parameters

        Returns:
            Dictionary containing execution results
        """
        action = task.get("action", "health_check")
        start_time = time.time()

        try:
            self._set_status(AgentStatus.RUNNING)

            if action == "health_check":
                result = await self._perform_health_check()
            elif action == "collect_metrics":
                result = await self._collect_all_metrics()
            elif action == "get_dashboard_data":
                result = await self._get_dashboard_data(task.get("time_range", "1h"))
            elif action == "get_agent_health":
                agent_id = task.get("agent_id")
                result = await self._get_agent_health(agent_id)
            elif action == "get_service_health":
                service_name = task.get("service_name")
                result = await self._get_service_health(service_name)
            elif action == "trigger_alert":
                result = await self._trigger_alert(
                    task.get("level", "warning"),
                    task.get("title", "Manual Alert"),
                    task.get("message", ""),
                    task.get("metadata"),
                )
            else:
                raise AgentError(f"Unknown action: {action}", agent_id=self.agent_id)

            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, True)

            return {
                "success": True,
                "action": action,
                "result": result,
                "execution_time": execution_time,
            }
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, False)
            logger.error(f"Task execution failed: {e}", exc_info=True)
            raise AgentError(f"Task execution failed: {e}", agent_id=self.agent_id) from e
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("Monitoring loop started")
        last_health_check = 0

        while self.status != AgentStatus.STOPPED:
            try:
                current_time = time.time()

                # Periodic health checks
                if current_time - last_health_check >= self._health_check_interval:
                    await self._perform_health_check()
                    last_health_check = current_time

                # Collect metrics
                await self._collect_all_metrics()

                # Check thresholds and trigger alerts
                await self._check_thresholds()

                # Wait for next interval
                await asyncio.sleep(self._monitoring_interval)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self._monitoring_interval)

    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_data = {
            "timestamp": time.time(),
            "agents": {},
            "services": {},
            "system_resources": {},
            "overall_healthy": True,
        }

        # Check all agents
        if self.registry:
            try:
                agents_health = await self.registry.aggregate_health()
                health_data["agents"] = agents_health
                health_data["overall_healthy"] = health_data["overall_healthy"] and agents_health.get(
                    "overall_healthy", True
                )
            except Exception as e:
                logger.error(f"Error checking agents health: {e}", exc_info=True)
                health_data["agents"] = {"error": str(e)}

        # Check services
        health_data["services"] = await self._check_services_health()

        # Check system resources
        health_data["system_resources"] = await self._check_system_resources()

        # Store in history
        self.metrics_history["agent_health"].append(health_data)

        # Record metric
        self.record_metric("health_check_duration", time.time() - health_data["timestamp"])

        return health_data

    async def _check_services_health(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all services"""
        services = {}

        # Supabase
        services["supabase"] = await self._check_supabase_health()

        # Redis
        services["redis"] = await self._check_redis_health()

        # Database (via DatabaseAgent if available)
        services["database"] = await self._check_database_health()

        return services

    async def _check_supabase_health(self) -> Dict[str, Any]:
        """Check Supabase health"""
        if not self._supabase_manager:
            return {"status": "not_configured", "healthy": False}

        try:
            start_time = time.time()
            # Simple query to check connectivity
            client = self._supabase_manager.client
            if client:
                # Try a simple query
                response = client.table("posts").select("id").limit(1).execute()
                response_time = (time.time() - start_time) * 1000  # ms

                return {
                    "status": "healthy",
                    "healthy": True,
                    "response_time_ms": response_time,
                    "checked_at": time.time(),
                }
            else:
                return {"status": "error", "healthy": False, "error": "Client not initialized"}
        except Exception as e:
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e),
                "checked_at": time.time(),
            }

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        if not self._redis_client:
            return {"status": "not_configured", "healthy": False}

        try:
            start_time = time.time()
            self._redis_client.ping()
            response_time = (time.time() - start_time) * 1000  # ms

            return {
                "status": "healthy",
                "healthy": True,
                "response_time_ms": response_time,
                "checked_at": time.time(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e),
                "checked_at": time.time(),
            }

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            from src.services.new_database_manager import get_database_manager

            db = get_database_manager()
            start_time = time.time()
            posts = db.get_posts(limit=1)
            response_time = (time.time() - start_time) * 1000  # ms

            return {
                "status": "healthy",
                "healthy": True,
                "response_time_ms": response_time,
                "checked_at": time.time(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e),
                "checked_at": time.time(),
            }

    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            resources = {
                "cpu": {
                    "percent": cpu_percent,
                    "status": "normal" if cpu_percent < 80 else "high",
                },
                "memory": {
                    "used_gb": round(memory.used / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "percent": memory.percent,
                    "status": "normal" if memory.percent < 80 else "high",
                },
                "disk": {
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent,
                    "status": "normal" if disk.percent < 90 else "low",
                },
                "checked_at": time.time(),
            }

            # Store in history
            self.metrics_history["system_resources"].append(resources)

            return resources
        except Exception as e:
            logger.error(f"Error checking system resources: {e}", exc_info=True)
            return {"error": str(e), "checked_at": time.time()}

    async def _collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all metrics"""
        metrics = {
            "timestamp": time.time(),
            "agent_metrics": {},
            "application_metrics": {},
            "database_metrics": {},
            "business_metrics": {},
        }

        # Agent metrics (including specialized agents)
        if self.registry:
            for agent_id, agent in self.registry._agents.items():
                try:
                    agent_metrics = agent.get_metrics()
                    metrics["agent_metrics"][agent_id] = agent_metrics
                except Exception as e:
                    logger.debug(f"Error getting metrics for agent {agent_id}: {e}")
            
            # Explicitly check specialized agents for enhanced metrics
            specialized_agents = ["analyst", "skeptic", "historian"]
            for agent_id in specialized_agents:
                agent = self.registry.get_agent(agent_id)
                if agent:
                    try:
                        # Get enhanced health check which includes specialized metrics
                        health = await agent.health_check()
                        if agent_id not in metrics["agent_metrics"]:
                            metrics["agent_metrics"][agent_id] = {}
                        # Add specialized health data
                        metrics["agent_metrics"][agent_id]["health"] = health
                    except Exception as e:
                        logger.debug(f"Error getting health for specialized agent {agent_id}: {e}")

        # Application metrics
        metrics["application_metrics"] = await self._collect_application_metrics()

        # Database metrics
        metrics["database_metrics"] = await self._collect_database_metrics()

        # Business metrics
        metrics["business_metrics"] = await self._collect_business_metrics()

        # Store in history
        self.metrics_history["performance"].append(metrics)

        return metrics

    async def _collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application-level metrics"""
        # Safe access to registry agents
        if not self.registry or not hasattr(self.registry, "_agents"):
            return {
                "active_agents": 0,
                "total_tasks": 0,
                "failed_tasks": 0,
                "avg_execution_time": self.metrics.get("execution_time_avg", 0.0),
            }

        agents = self.registry._agents.values()
        return {
            "active_agents": len(self.registry._agents),
            "total_tasks": sum(agent.metrics.get("tasks_total", 0) for agent in agents),
            "failed_tasks": sum(agent.metrics.get("tasks_failed", 0) for agent in agents),
            "avg_execution_time": self.metrics.get("execution_time_avg", 0.0),
        }

    async def _collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database metrics"""
        try:
            from src.services.new_database_manager import get_database_manager

            db = get_database_manager()
            posts = db.get_posts(limit=10000)

            # Count posts from last 24 hours
            # Handle both dict and object access patterns
            cutoff_time = datetime.now() - timedelta(hours=24)
            posts_last_24h = 0

            for p in posts:
                try:
                    # Try dict access first
                    if isinstance(p, dict):
                        created_at_str = p.get("created_at")
                    else:
                        # Try object attribute access
                        created_at_str = getattr(p, "created_at", None)

                    if created_at_str:
                        created_at = datetime.fromisoformat(str(created_at_str))
                        if created_at > cutoff_time:
                            posts_last_24h += 1
                except (ValueError, TypeError, AttributeError):
                    # Skip posts with invalid or missing created_at
                    continue

            return {
                "total_posts": len(posts),
                "posts_last_24h": posts_last_24h,
            }
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}", exc_info=True)
            return {"error": str(e)}

    async def _collect_business_metrics(self) -> Dict[str, Any]:
        """Collect business metrics"""
        # This can be extended with business-specific metrics
        return {
            "alerts_sent": len([a for a in self.metrics_history["alerts"] if a.get("sent", False)]),
            "health_checks_performed": len(self.metrics_history["agent_health"]),
        }

    async def _check_thresholds(self) -> None:
        """Check alert thresholds and trigger alerts if needed"""
        # Get latest system resources
        if not self.metrics_history["system_resources"]:
            return

        latest_resources = self.metrics_history["system_resources"][-1]

        # Check CPU threshold
        cpu_percent = latest_resources.get("cpu", {}).get("percent", 0)
        if cpu_percent > self._alert_thresholds.get("cpu_percent", 80):
            await self._trigger_alert(
                "warning",
                "High CPU Usage",
                f"CPU usage is {cpu_percent:.1f}% (threshold: {self._alert_thresholds.get('cpu_percent', 80)}%)",
                {"cpu_percent": cpu_percent, "threshold": self._alert_thresholds.get("cpu_percent", 80)},
                alert_key="high_cpu",
            )

        # Check memory threshold
        memory_percent = latest_resources.get("memory", {}).get("percent", 0)
        if memory_percent > self._alert_thresholds.get("memory_percent", 80):
            await self._trigger_alert(
                "warning",
                "High Memory Usage",
                f"Memory usage is {memory_percent:.1f}% (threshold: {self._alert_thresholds.get('memory_percent', 80)}%)",
                {"memory_percent": memory_percent, "threshold": self._alert_thresholds.get("memory_percent", 80)},
                alert_key="high_memory",
            )

        # Check disk threshold
        disk_percent = latest_resources.get("disk", {}).get("percent", 0)
        if disk_percent > self._alert_thresholds.get("disk_percent", 90):
            await self._trigger_alert(
                "critical",
                "Low Disk Space",
                f"Disk usage is {disk_percent:.1f}% (threshold: {self._alert_thresholds.get('disk_percent', 90)}%)",
                {"disk_percent": disk_percent, "threshold": self._alert_thresholds.get("disk_percent", 90)},
                alert_key="low_disk",
            )

        # Check agent failures
        if self.registry:
            agents_health = await self.registry.aggregate_health()
            unhealthy_count = agents_health.get("unhealthy_agents", 0)
            if unhealthy_count > 0:
                await self._trigger_alert(
                    "warning",
                    "Unhealthy Agents",
                    f"{unhealthy_count} agent(s) are unhealthy",
                    {"unhealthy_count": unhealthy_count, "agents": agents_health.get("agents", {})},
                    alert_key="unhealthy_agents",
                )

        # Check service failures
        services_health = await self._check_services_health()
        unhealthy_services = [
            name for name, health in services_health.items() if not health.get("healthy", False)
        ]
        if unhealthy_services:
            await self._trigger_alert(
                "critical" if len(unhealthy_services) > 1 else "warning",
                "Service Failure",
                f"Service(s) unhealthy: {', '.join(unhealthy_services)}",
                {"unhealthy_services": unhealthy_services},
                alert_key="service_failure",
            )

    async def _trigger_alert(
        self,
        level: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        alert_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trigger an alert through all configured channels.

        Args:
            level: Alert level (info, warning, critical)
            title: Alert title
            message: Alert message
            metadata: Optional metadata
            alert_key: Optional key for cooldown tracking

        Returns:
            Dictionary with alert results
        """
        # Check cooldown
        if alert_key:
            cooldown_seconds = self.config.get("alert_cooldown_seconds", 300)
            last_alert_time = self._alert_cooldown.get(alert_key, 0)
            if time.time() - last_alert_time < cooldown_seconds:
                logger.debug(f"Alert {alert_key} in cooldown, skipping")
                return {"sent": False, "reason": "cooldown"}

        # Send through all channels
        results = {}
        for channel in self.alert_channels:
            channel_result = await channel.send_alert(level, title, message, metadata)
            results[channel.channel_type] = channel_result

        # Record alert
        alert_record = {
            "timestamp": time.time(),
            "level": level,
            "title": title,
            "message": message,
            "metadata": metadata or {},
            "sent": any(results.values()),
            "channels": results,
        }
        self.metrics_history["alerts"].append(alert_record)

        # Update cooldown
        if alert_key:
            self._alert_cooldown[alert_key] = time.time()

        # Record metric
        self.record_metric("alerts_sent", 1, tags={"level": level})

        return alert_record

    async def _get_dashboard_data(self, time_range: str = "1h") -> Dict[str, Any]:
        """
        Get aggregated data for dashboard.

        Args:
            time_range: Time range (e.g., "1h", "24h", "7d")

        Returns:
            Dictionary with dashboard data
        """
        # Parse time range
        time_delta = self._parse_time_range(time_range)
        cutoff_time = time.time() - time_delta.total_seconds()

        # Filter metrics by time range
        agent_health_recent = [
            h for h in self.metrics_history["agent_health"] if h.get("timestamp", 0) >= cutoff_time
        ]
        performance_recent = [
            m for m in self.metrics_history["performance"] if m.get("timestamp", 0) >= cutoff_time
        ]
        system_resources_recent = [
            r for r in self.metrics_history["system_resources"] if r.get("checked_at", 0) >= cutoff_time
        ]

        # Aggregate data
        dashboard_data = {
            "time_range": time_range,
            "timestamp": time.time(),
            "real_time": {
                "system_resources": system_resources_recent[-1] if system_resources_recent else {},
                "agent_health": agent_health_recent[-1] if agent_health_recent else {},
            },
            "historical": {
                "system_resources": system_resources_recent,
                "performance": performance_recent,
                "agent_health": agent_health_recent,
            },
            "trends": self._calculate_trends(performance_recent, system_resources_recent),
        }

        return dashboard_data

    def _parse_time_range(self, time_range: str) -> timedelta:
        """Parse time range string to timedelta"""
        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            return timedelta(hours=hours)
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            return timedelta(days=days)
        elif time_range.endswith("m"):
            minutes = int(time_range[:-1])
            return timedelta(minutes=minutes)
        else:
            return timedelta(hours=1)  # Default

    def _calculate_trends(
        self, performance_data: List[Dict[str, Any]], resources_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate trends from historical data"""
        trends = {}

        # CPU trend
        if resources_data:
            cpu_values = [r.get("cpu", {}).get("percent", 0) for r in resources_data]
            if len(cpu_values) > 1:
                trends["cpu"] = {
                    "current": cpu_values[-1],
                    "average": sum(cpu_values) / len(cpu_values),
                    "trend": "increasing" if cpu_values[-1] > cpu_values[0] else "decreasing",
                }

        # Memory trend
        if resources_data:
            memory_values = [r.get("memory", {}).get("percent", 0) for r in resources_data]
            if len(memory_values) > 1:
                trends["memory"] = {
                    "current": memory_values[-1],
                    "average": sum(memory_values) / len(memory_values),
                    "trend": "increasing" if memory_values[-1] > memory_values[0] else "decreasing",
                }

        return trends

    async def _get_agent_health(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get health status for specific agent or all agents"""
        if agent_id:
            agent = self.registry.get_agent(agent_id) if self.registry else None
            if agent:
                return await agent.health_check()
            else:
                return {"error": f"Agent {agent_id} not found"}
        else:
            if self.registry:
                return await self.registry.aggregate_health()
            else:
                return {"error": "Registry not available"}

    async def _get_service_health(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get health status for specific service or all services"""
        services = await self._check_services_health()
        if service_name:
            return services.get(service_name, {"error": f"Service {service_name} not found"})
        else:
            return services

    async def shutdown(self) -> None:
        """Shutdown the monitoring agent gracefully"""
        logger.info("Shutting down Monitoring Agent...")

        # Stop monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        # Close service connections
        if self._redis_client:
            try:
                self._redis_client.close()
            except Exception:
                pass

        await super().shutdown()

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the monitoring agent itself.

        Returns:
            Dictionary with health check results
        """
        base_health = await super().health_check()

        # Add monitoring-specific health
        monitoring_health = {
            **base_health,
            "monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done(),
            "metrics_collected": {
                "agent_health": len(self.metrics_history["agent_health"]),
                "performance": len(self.metrics_history["performance"]),
                "alerts": len(self.metrics_history["alerts"]),
            },
            "alert_channels": len(self.alert_channels),
            "last_health_check": self._last_health_check,
        }

        return monitoring_health

