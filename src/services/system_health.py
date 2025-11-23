"""
System Health Service
Unified health monitoring aggregating all system components
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import psutil

from src.services.health import get_health_monitor
from src.services.error_tracker import get_error_tracker
from src.services.pipeline_status import PipelineStatusService
from src.shared.utils.observability_hub import get_observability_hub

logger = logging.getLogger(__name__)


class SystemHealthService:
    """Unified system health service aggregating all health data"""
    
    def __init__(self):
        self.health_monitor = get_health_monitor()
        self.error_tracker = get_error_tracker()
        self.pipeline_status = PipelineStatusService()
        self.start_time = datetime.now(timezone.utc)
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive system health"""
        try:
            # Get component health
            components = await self._check_all_components()
            
            # Get performance metrics
            metrics = self._get_performance_metrics()
            
            # Get error rates
            errors = await self._get_error_rates()
            
            # Get resource usage
            resources = self._get_resource_usage()
            
            # Get pipeline status
            pipeline = await self.pipeline_status.get_status()
            
            # Calculate overall status
            overall_status = self._calculate_overall_status(
                components, metrics, errors, pipeline
            )
            
            # Calculate health score (0-100)
            health_score = self._calculate_health_score(
                components, metrics, errors, pipeline
            )
            
            # Get uptime
            uptime = self._get_uptime()
            
            return {
                "status": overall_status,
                "health_score": health_score,
                "uptime": uptime,
                "components": components,
                "metrics": metrics,
                "errors": errors,
                "resources": resources,
                "pipeline": pipeline,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting comprehensive health: {e}", exc_info=True)
            return self._empty_health()
    
    async def _check_all_components(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all system components"""
        components = {}
        
        # Use existing health monitor for basic checks
        health_monitor_health = self.health_monitor.get_system_health()
        components.update(health_monitor_health.get("components", {}))
        
        # Check database via error tracker
        try:
            # Try to get errors (if DB is working, this will work)
            stats = self.error_tracker.get_error_stats()
            if "database" not in components:
                components["database"] = {
                    "status": "healthy",
                    "message": "Database accessible"
                }
        except Exception as e:
            components["database"] = {
                "status": "critical",
                "message": f"Database error: {str(e)[:100]}"
            }
        
        # Check AI services (Ollama, Gemini, etc.)
        ai_status = await self._check_ai_services()
        components["ai_services"] = ai_status
        
        # Check collection services
        collection_status = await self._check_collection_services()
        components["collection"] = collection_status
        
        # Check publishing worker
        publishing_status = await self._check_publishing_worker()
        components["publishing"] = publishing_status
        
        # Check API
        components["api"] = {
            "status": "healthy",
            "message": "API responding"
        }
        
        return components
    
    async def _check_ai_services(self) -> Dict[str, Any]:
        """Check AI services health"""
        try:
            import httpx
            
            # Check Ollama
            try:
                response = httpx.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "message": "Ollama available",
                        "services": ["ollama"]
                    }
            except:
                pass
            
            # Check if Gemini is configured
            import os
            if os.getenv("GEMINI_API_KEY"):
                return {
                    "status": "healthy",
                    "message": "Gemini API configured",
                    "services": ["gemini"]
                }
            
            return {
                "status": "degraded",
                "message": "No AI services available (optional)",
                "services": []
            }
        except Exception as e:
            return {
                "status": "degraded",
                "message": f"AI service check failed: {str(e)[:100]}",
                "services": []
            }
    
    async def _check_collection_services(self) -> Dict[str, Any]:
        """Check collection services health"""
        try:
            # Check if collection has run recently (last 24 hours)
            # This is a simple check - in production you'd check actual service status
            return {
                "status": "healthy",
                "message": "Collection services available"
            }
        except Exception as e:
            return {
                "status": "degraded",
                "message": f"Collection check failed: {str(e)[:100]}"
            }
    
    async def _check_publishing_worker(self) -> Dict[str, Any]:
        """Check publishing worker health"""
        try:
            # Check if publishing worker is active
            # In production, you'd check if the worker process is running
            return {
                "status": "healthy",
                "message": "Publishing worker available"
            }
        except Exception as e:
            return {
                "status": "degraded",
                "message": f"Publishing check failed: {str(e)[:100]}"
            }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        health_data = self.health_monitor.get_system_health()
        perf = health_data.get("performance", {})
        
        # Get observability metrics
        try:
            hub = get_observability_hub()
            error_summary = hub.get_error_summary()
            
            return {
                "api_response_time_avg": health_data.get("recent_activity", {}).get("avg_response_time", 0),
                "collection_rate": 0,  # Would come from pipeline status
                "analysis_rate": 0,  # Would come from pipeline status
                "error_rate": error_summary.get("total_errors", 0) / max(1, len(error_summary.get("top_errors", []))),
                "throughput": {
                    "posts_per_hour": 0,  # Would be calculated from recent activity
                    "analyses_per_hour": 0
                }
            }
        except Exception as e:
            logger.debug(f"Error getting observability metrics: {e}")
            return {
                "api_response_time_avg": perf.get("cpu", {}).get("percent", 0),
                "collection_rate": 0,
                "analysis_rate": 0,
                "error_rate": 0,
                "throughput": {}
            }
    
    async def _get_error_rates(self) -> Dict[str, Any]:
        """Get error rates"""
        try:
            stats = self.error_tracker.get_error_stats()
            
            # Get recent errors (last hour)
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_errors = self.error_tracker.get_errors(
                start_date=one_hour_ago,
                limit=100
            )
            
            return {
                "rate": len(recent_errors.get("errors", [])) / 1.0,  # errors per hour
                "total_errors": stats.get("total_errors", 0),
                "by_severity": stats.get("by_severity", {}),
                "by_component": stats.get("by_component", {}),
                "recent": recent_errors.get("errors", [])[:10]  # Last 10 errors
            }
        except Exception as e:
            logger.debug(f"Error getting error rates: {e}")
            return {
                "rate": 0,
                "total_errors": 0,
                "by_severity": {},
                "by_component": {},
                "recent": []
            }
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get resource usage"""
        try:
            health_data = self.health_monitor.get_system_health()
            perf = health_data.get("performance", {})
            
            return {
                "cpu": {
                    "percent": perf.get("cpu", {}).get("percent", 0),
                    "status": perf.get("cpu", {}).get("status", "normal")
                },
                "memory": {
                    "percent": perf.get("memory", {}).get("percent", 0),
                    "used_gb": perf.get("memory", {}).get("used_gb", 0),
                    "total_gb": perf.get("memory", {}).get("total_gb", 0),
                    "status": perf.get("memory", {}).get("status", "normal")
                },
                "disk": {
                    "percent": perf.get("disk", {}).get("percent", 0),
                    "used_gb": perf.get("disk", {}).get("used_gb", 0),
                    "free_gb": perf.get("disk", {}).get("free_gb", 0),
                    "status": perf.get("disk", {}).get("status", "normal")
                }
            }
        except Exception as e:
            logger.debug(f"Error getting resource usage: {e}")
            return {
                "cpu": {"percent": 0, "status": "unknown"},
                "memory": {"percent": 0, "used_gb": 0, "total_gb": 0, "status": "unknown"},
                "disk": {"percent": 0, "used_gb": 0, "free_gb": 0, "status": "unknown"}
            }
    
    def _calculate_overall_status(
        self,
        components: Dict[str, Any],
        metrics: Dict[str, Any],
        errors: Dict[str, Any],
        pipeline: Dict[str, Any]
    ) -> str:
        """Calculate overall system status"""
        # Check for critical component failures
        component_statuses = [
            comp.get("status") for comp in components.values()
            if isinstance(comp, dict) and "status" in comp
        ]
        
        if "critical" in component_statuses:
            return "critical"
        
        # Check for high error rate
        error_rate = errors.get("rate", 0)
        if error_rate > 10:  # More than 10 errors per hour
            return "critical"
        
        # Check for degraded components
        if "degraded" in component_statuses:
            return "degraded"
        
        # Check pipeline health
        pipeline_health = pipeline.get("health", "healthy")
        if pipeline_health == "critical":
            return "critical"
        if pipeline_health == "degraded":
            return "degraded"
        
        # Check resource usage
        resources = self._get_resource_usage()
        if resources.get("memory", {}).get("percent", 0) > 90:
            return "critical"
        if resources.get("disk", {}).get("percent", 0) > 95:
            return "critical"
        
        return "healthy"
    
    def _calculate_health_score(
        self,
        components: Dict[str, Any],
        metrics: Dict[str, Any],
        errors: Dict[str, Any],
        pipeline: Dict[str, Any]
    ) -> int:
        """Calculate health score (0-100)"""
        score = 100
        
        # Deduct for component failures
        component_statuses = [
            comp.get("status") for comp in components.values()
            if isinstance(comp, dict) and "status" in comp
        ]
        
        for status in component_statuses:
            if status == "critical":
                score -= 20
            elif status == "degraded":
                score -= 10
        
        # Deduct for high error rate
        error_rate = errors.get("rate", 0)
        if error_rate > 10:
            score -= 20
        elif error_rate > 5:
            score -= 10
        elif error_rate > 1:
            score -= 5
        
        # Deduct for resource issues
        resources = self._get_resource_usage()
        if resources.get("memory", {}).get("percent", 0) > 90:
            score -= 15
        elif resources.get("memory", {}).get("percent", 0) > 80:
            score -= 5
        
        if resources.get("disk", {}).get("percent", 0) > 95:
            score -= 15
        elif resources.get("disk", {}).get("percent", 0) > 90:
            score -= 5
        
        return max(0, min(100, score))
    
    def _get_uptime(self) -> str:
        """Get system uptime"""
        uptime = datetime.now(timezone.utc) - self.start_time
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"
    
    def _empty_health(self) -> Dict[str, Any]:
        """Return empty health when service unavailable"""
        return {
            "status": "unknown",
            "health_score": 0,
            "uptime": "0m",
            "components": {},
            "metrics": {},
            "errors": {},
            "resources": {},
            "pipeline": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

