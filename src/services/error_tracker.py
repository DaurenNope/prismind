"""
Error Tracking Service
Tracks and stores errors in the database for dashboard display
"""
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class ErrorTracker:
    """Service for tracking and storing errors"""
    
    def __init__(self, supabase=None):
        """Initialize with optional Supabase client"""
        self.supabase = supabase
        if not self.supabase:
            try:
                from src.infrastructure.database.manager import SupabaseManager
                manager = SupabaseManager()
                self.supabase = manager.client
            except Exception as e:
                logger.warning(f"Could not initialize Supabase client for error tracking: {e}")
                self.supabase = None
    
    def track_error(
        self,
        component: str,
        error: Exception,
        severity: str = "error",
        context: Optional[Dict[str, Any]] = None,
        auto_resolve: bool = False
    ) -> Optional[str]:
        """Track an error in the database"""
        if not self.supabase:
            logger.debug("Supabase not available, skipping error tracking")
            return None
        
        try:
            error_type = type(error).__name__
            message = str(error)
            stack_trace = traceback.format_exc()
            
            # Check if similar error exists (same component, type, message)
            # If so, increment count instead of creating new entry
            existing = (
                self.supabase.table("system_errors")
                .select("id, count")
                .eq("component", component)
                .eq("error_type", error_type)
                .eq("message", message)
                .eq("status", "open")
                .limit(1)
                .execute()
            )
            
            if existing.data and len(existing.data) > 0:
                # Increment count
                error_id = existing.data[0]["id"]
                current_count = existing.data[0].get("count", 1)
                (
                    self.supabase.table("system_errors")
                    .update({
                        "count": current_count + 1,
                        "created_at": datetime.now(timezone.utc).isoformat()  # Update timestamp
                    })
                    .eq("id", error_id)
                    .execute()
                )
                return str(error_id)
            else:
                # Create new error entry
                error_data = {
                    "component": component,
                    "error_type": error_type,
                    "message": message,
                    "stack_trace": stack_trace,
                    "severity": severity,
                    "status": "resolved" if auto_resolve else "open",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": context or {},
                    "count": 1
                }
                
                result = (
                    self.supabase.table("system_errors")
                    .insert(error_data)
                    .execute()
                )
                
                if result.data and len(result.data) > 0:
                    return str(result.data[0]["id"])
                return None
        except Exception as e:
            logger.error(f"Error tracking error: {e}", exc_info=True)
            return None
    
    def get_errors(
        self,
        component: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get list of errors with filters"""
        if not self.supabase:
            return {"errors": [], "total": 0, "limit": limit, "offset": offset}
        
        try:
            query = self.supabase.table("system_errors").select("*")
            
            if component:
                query = query.eq("component", component)
            if severity:
                query = query.eq("severity", severity)
            if status:
                query = query.eq("status", status)
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            # Get total count
            count_query = query.select("id", count="exact")
            count_result = count_query.execute()
            total = getattr(count_result, "count", 0) or 0
            
            # Apply ordering and pagination
            query = query.order("created_at", desc=True).limit(limit).offset(offset)
            result = query.execute()
            
            return {
                "errors": result.data or [],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Error getting errors: {e}", exc_info=True)
            return {"errors": [], "total": 0, "limit": limit, "offset": offset}
    
    def get_error_details(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Get full error details"""
        if not self.supabase:
            return None
        
        try:
            result = (
                self.supabase.table("system_errors")
                .select("*")
                .eq("id", error_id)
                .single()
                .execute()
            )
            
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting error details: {e}", exc_info=True)
            return None
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.supabase:
            return self._empty_stats()
        
        try:
            # Get all errors
            all_errors = (
                self.supabase.table("system_errors")
                .select("component, severity, status")
                .execute()
            ).data or []
            
            total_errors = len(all_errors)
            
            # Count by component
            by_component = defaultdict(int)
            for error in all_errors:
                component = error.get("component", "unknown")
                by_component[component] += 1
            
            # Count by severity
            by_severity = defaultdict(int)
            for error in all_errors:
                severity = error.get("severity", "error")
                by_severity[severity] += 1
            
            # Count by status
            by_status = defaultdict(int)
            resolved_count = 0
            for error in all_errors:
                status = error.get("status", "open")
                by_status[status] += 1
                if status == "resolved":
                    resolved_count += 1
            
            # Calculate resolution rate
            resolution_rate = (resolved_count / total_errors) if total_errors > 0 else 0.0
            
            return {
                "total_errors": total_errors,
                "by_component": dict(by_component),
                "by_severity": dict(by_severity),
                "by_status": dict(by_status),
                "resolution_rate": round(resolution_rate, 2)
            }
        except Exception as e:
            logger.error(f"Error getting error stats: {e}", exc_info=True)
            return self._empty_stats()
    
    def resolve_error(self, error_id: str, resolution_notes: Optional[str] = None) -> bool:
        """Mark error as resolved"""
        if not self.supabase:
            return False
        
        try:
            (
                self.supabase.table("system_errors")
                .update({
                    "status": "resolved",
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "resolution_notes": resolution_notes
                })
                .eq("id", error_id)
                .execute()
            )
            return True
        except Exception as e:
            logger.error(f"Error resolving error: {e}", exc_info=True)
            return False
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty stats when service unavailable"""
        return {
            "total_errors": 0,
            "by_component": {},
            "by_severity": {},
            "by_status": {},
            "resolution_rate": 0.0
        }


# Global error tracker instance
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get global error tracker instance"""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker

