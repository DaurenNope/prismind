"""
Smart Alerting System for Beyondlines
Intelligent alerting with noise reduction and contextual awareness
"""

import asyncio
import json
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..utils.exceptions import BEYONDLINESException
from ..utils.logging_config import get_logger


class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Alert data structure"""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    component: str
    status: AlertStatus = AlertStatus.ACTIVE
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    occurrences: int = 1
    first_occurrence: datetime = field(default_factory=datetime.now)
    last_occurrence: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "component": self.component,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "occurrences": self.occurrences,
            "first_occurrence": self.first_occurrence.isoformat(),
            "last_occurrence": self.last_occurrence.isoformat(),
        }


class SmartAlerting:
    """Intelligent alerting system with noise reduction"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.suppression_rules: Dict[str, Any] = {}
        self.alert_cooldowns: Dict[str, datetime] = {}

        # Configuration
        self.config = {
            "max_alerts_per_minute": 10,
            "alert_aggregation_window": 300,  # 5 minutes
            "duplicate_suppression": 60,  # 1 minute
            "critical_immediate": True,
            "email_enabled": True,
            "slack_enabled": False,
            "alert_retention_days": 30,
        }

        # Alert statistics
        self.stats = {
            "total_alerts": 0,
            "alerts_by_severity": {level.value: 0 for level in AlertSeverity},
            "alerts_by_component": {},
            "suppressed_alerts": 0,
            "false_positives": 0,
        }

    async def process_alert(self, alert_data: Dict[str, Any]) -> Optional[Alert]:
        """Process an incoming alert"""
        try:
            # Create alert object
            alert = self._create_alert(alert_data)

            # Check if this is a duplicate or should be suppressed
            if await self._should_suppress_alert(alert):
                self.logger.debug(f"Alert suppressed: {alert.id}")
                return None

            # Update or create alert
            existing_alert = self.active_alerts.get(alert.id)
            if existing_alert:
                existing_alert.occurrences += 1
                existing_alert.last_occurrence = datetime.now()
                existing_alert.metadata.update(alert.metadata)
                alert = existing_alert

            # Add to active alerts
            self.active_alerts[alert.id] = alert

            # Determine if alert should be sent
            if await self._should_send_alert(alert):
                await self._send_alert(alert)

            # Update statistics
            self._update_stats(alert)

            return alert

        except Exception as e:
            self.logger.error(f"Error processing alert: {e}")
            return None

    def _create_alert(self, alert_data: Dict[str, Any]) -> Alert:
        """Create alert object from data"""
        alert_id = self._generate_alert_id(alert_data)

        return Alert(
            id=alert_id,
            title=alert_data.get("title", "Unknown Alert"),
            description=alert_data.get("description", ""),
            severity=AlertSeverity(alert_data.get("severity", "medium")),
            component=alert_data.get("component", "unknown"),
            metadata=alert_data.get("metadata", {}),
            timestamp=datetime.fromisoformat(
                alert_data.get("timestamp", datetime.now().isoformat())
            ),
        )

    def _generate_alert_id(self, alert_data: Dict[str, Any]) -> str:
        """Generate unique alert ID"""
        import hashlib

        # Create hash from alert content for deduplication
        content = f"{alert_data.get('component', '')}-{alert_data.get('title', '')}-{alert_data.get('description', '')}"
        hash_obj = hashlib.md5(content.encode())
        return hash_obj.hexdigest()[:16]

    async def _should_suppress_alert(self, alert: Alert) -> bool:
        """Determine if alert should be suppressed"""

        # Check alert cooldown
        if alert.id in self.alert_cooldowns:
            if datetime.now() < self.alert_cooldowns[alert.id]:
                self.stats["suppressed_alerts"] += 1
                return True
            else:
                del self.alert_cooldowns[alert.id]

        # Check alert storms
        if await self._is_alert_storm():
            if alert.severity not in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                self.stats["suppressed_alerts"] += 1
                return True

        # Check duplicate suppression
        if await self._is_duplicate_alert(alert):
            self.stats["suppressed_alerts"] += 1
            return True

        # Check suppression rules
        if await self._matches_suppression_rule(alert):
            self.stats["suppressed_alerts"] += 1
            return True

        return False

    async def _should_send_alert(self, alert: Alert) -> bool:
        """Determine if alert should be sent"""

        # Critical alerts always go through
        if (
            alert.severity == AlertSeverity.CRITICAL
            and self.config["critical_immediate"]
        ):
            return True

        # Check rate limiting
        if await self._is_rate_limited():
            return False

        # Check if it's the first occurrence
        if alert.occurrences == 1:
            return True

        # Check if it's been long enough since last notification
        time_since_last = datetime.now() - alert.last_occurrence
        if time_since_last < timedelta(minutes=5):
            return False

        # Check escalation
        escalation_threshold = {
            AlertSeverity.HIGH: 3,
            AlertSeverity.MEDIUM: 5,
            AlertSeverity.LOW: 10,
        }

        threshold = escalation_threshold.get(alert.severity, 5)
        if alert.occurrences >= threshold:
            return True

        return False

    async def _send_alert(self, alert: Alert):
        """Send alert through appropriate channels"""
        self.logger.info(f"🚨 ALERT: [{alert.severity.value.upper()}] {alert.title}")

        # Add to history
        self.alert_history.append(alert)

        # Send email
        if self.config["email_enabled"]:
            await self._send_email_alert(alert)

        # Send Slack
        if self.config["slack_enabled"]:
            await self._send_slack_alert(alert)

        # Store for persistence
        await self._persist_alert(alert)

    async def _send_email_alert(self, alert: Alert):
        """Send email alert"""
        try:
            if not self._get_email_config():
                self.logger.warning("Email configuration not available")
                return

            email_config = self._get_email_config()

            # Create email
            msg = MimeMultipart()
            msg["From"] = email_config["from"]
            msg["To"] = email_config["to"]
            msg[
                "Subject"
            ] = f"[{alert.severity.value.upper()}] Beyondlines Alert: {alert.title}"

            # Email body
            body = self._format_email_body(alert)
            msg.attach(MimeText(body, "plain"))

            # Send email
            server = smtplib.SMTP(
                email_config["smtp_server"], email_config["smtp_port"]
            )
            server.starttls()
            server.login(email_config["smtp_user"], email_config["smtp_password"])
            server.send_message(msg)
            server.quit()

            self.logger.info(f"✅ Email alert sent for {alert.id}")

        except Exception as e:
            self.logger.error(f"❌ Failed to send email alert: {e}")

    async def _send_slack_alert(self, alert: Alert):
        """Send Slack alert"""
        try:
            slack_config = self._get_slack_config()
            if not slack_config:
                self.logger.warning("Slack configuration not available")
                return

            import aiohttp

            # Format Slack message
            slack_message = self._format_slack_message(alert)

            # Send to Slack
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {slack_config['bot_token']}",
                    "Content-Type": "application/json",
                }

                payload = {"channel": slack_config["channel"], "text": slack_message}

                async with session.post(
                    "https://slack.com/api/chat.postMessage",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"✅ Slack alert sent for {alert.id}")
                    else:
                        self.logger.error(
                            f"❌ Failed to send Slack alert: {response.status}"
                        )

        except Exception as e:
            self.logger.error(f"❌ Failed to send Slack alert: {e}")

    def _format_email_body(self, alert: Alert) -> str:
        """Format email body"""
        return f"""
Beyondlines Alert Notification
=====================================

Severity: {alert.severity.value.upper()}
Component: {alert.component}
Title: {alert.title}
Description: {alert.description}

Occurrences: {alert.occurrences}
First Occurrence: {alert.first_occurrence.isoformat()}
Last Occurrence: {alert.last_occurrence.isoformat()}

Metadata:
{json.dumps(alert.metadata, indent=2)}

Timestamp: {alert.timestamp.isoformat()}

--
Beyondlines Autonomous System
        """.strip()

    def _format_slack_message(self, alert: Alert) -> str:
        """Format Slack message"""
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📢",
            "low": "ℹ️",
            "info": "ℹ️",
        }

        emoji = severity_emoji.get(alert.severity.value, "📢")

        return f"""
{emoji} **{alert.title}**

*Component:* {alert.component}
*Severity:* {alert.severity.value.upper()}
*Occurrences:* {alert.occurrences}
*Description:* {alert.description}

*Timestamp:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
        """.strip()

    async def _persist_alert(self, alert: Alert):
        """Persist alert to storage"""
        try:
            # This would integrate with your database system
            # For now, just log it
            self.logger.debug(f"Persisting alert: {alert.id}")

        except Exception as e:
            self.logger.error(f"Failed to persist alert {alert.id}: {e}")

    async def _is_alert_storm(self) -> bool:
        """Check if we're in an alert storm"""
        recent_alerts = [
            alert
            for alert in self.active_alerts.values()
            if (datetime.now() - alert.timestamp).total_seconds() < 60
        ]

        return len(recent_alerts) > self.config["max_alerts_per_minute"]

    async def _is_duplicate_alert(self, alert: Alert) -> bool:
        """Check if this is a duplicate alert"""
        if alert.id not in self.alert_cooldowns:
            return False

        cooldown_seconds = self.config["duplicate_suppression"]
        return datetime.now() < self.alert_cooldowns[alert.id]

    async def _matches_suppression_rule(self, alert: Alert) -> bool:
        """Check if alert matches any suppression rule"""
        # Add your suppression rules here
        suppression_rules = [
            # Suppress low-severity database warnings
            {
                "component": "database",
                "severity": ["low"],
                "title_contains": ["connection", "timeout"],
            }
        ]

        for rule in suppression_rules:
            if self._matches_rule(alert, rule):
                return True

        return False

    def _matches_rule(self, alert: Alert, rule: Dict[str, Any]) -> bool:
        """Check if alert matches a suppression rule"""
        if rule.get("component") and alert.component != rule["component"]:
            return False

        if rule.get("severity") and alert.severity.value not in rule["severity"]:
            return False

        if rule.get("title_contains"):
            title_lower = alert.title.lower()
            if not any(
                keyword.lower() in title_lower for keyword in rule["title_contains"]
            ):
                return False

        return True

    async def _is_rate_limited(self) -> bool:
        """Check if we're rate limited"""
        # Implementation would check recent send rates
        return False

    def _update_stats(self, alert: Alert):
        """Update alert statistics"""
        self.stats["total_alerts"] += 1
        self.stats["alerts_by_severity"][alert.severity.value] += 1

        if alert.component not in self.stats["alerts_by_component"]:
            self.stats["alerts_by_component"][alert.component] = 0
        self.stats["alerts_by_component"][alert.component] += 1

        # Set cooldown
        self.alert_cooldowns[alert.id] = datetime.now() + timedelta(
            seconds=self.config["duplicate_suppression"]
        )

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics"""
        return {
            "active_alerts": len(self.active_alerts),
            "total_alerts": self.stats["total_alerts"],
            "alerts_by_severity": self.stats["alerts_by_severity"],
            "alerts_by_component": self.stats["alerts_by_component"],
            "suppressed_alerts": self.stats["suppressed_alerts"],
            "recent_alerts": [
                alert.to_dict()
                for alert in sorted(
                    self.alert_history[-10:], key=lambda x: x.timestamp, reverse=True
                )
            ],
        }

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].status = AlertStatus.RESOLVED
            del self.active_alerts[alert_id]
            return True
        return False

    def _get_email_config(self) -> Optional[Dict[str, str]]:
        """Get email configuration"""
        import os

        config = {}
        required_fields = [
            "smtp_server",
            "smtp_port",
            "smtp_user",
            "smtp_password",
            "from",
            "to",
        ]

        for field in required_fields:
            value = os.getenv(f"ALERT_EMAIL_{field.upper()}")
            if not value:
                return None
            config[field] = value

        return config

    def _get_slack_config(self) -> Optional[Dict[str, str]]:
        """Get Slack configuration"""
        import os

        config = {}
        required_fields = ["bot_token", "channel"]

        for field in required_fields:
            value = os.getenv(f"ALERT_SLACK_{field.upper()}")
            if not value:
                return None
            config[field] = value

        return config


# Global alerting instance
smart_alerting = SmartAlerting()
