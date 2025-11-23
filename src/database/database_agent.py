#!/usr/bin/env python3
"""
DatabaseAgent

Centralized database operations layer for BEYONDLINES.
 - Supabase is the primary source of truth
 - SQLite is a local cache/mirror for resilience and fast reads
 - Validates schema-related fields and post payloads
 - Applies duplicate checking and normalized IDs/URLs
 - Provides health and recent-activity reports
 - Encapsulates retry/backoff for transient failures

Enhanced with BaseAgent integration:
 - Query optimization (slow query detection, index suggestions, query plan analysis)
 - Sync management (SQLite ↔ Supabase sync, conflict resolution, sync metrics)
 - Performance monitoring (query performance tracking, connection pool monitoring, alerts)
 - Comprehensive health checks (database connectivity, query performance, sync status, resource usage)
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.domain.intelligence.agents.base_agent import BaseAgent, AgentError, AgentStatus
from src.shared.utils.logging_config import get_logger
from src.shared.utils.observability_hub import get_observability_hub

logger = get_logger(__name__)


class DatabaseAgent(BaseAgent):
    """
    Enhanced Database Agent with BaseAgent integration.
    
    Inherits from BaseAgent and adds:
    - Query optimization features
    - Enhanced sync management
    - Performance monitoring
    - Comprehensive health checks
    """
    
    def __init__(
        self,
        agent_id: str = "database_agent",
        agent_name: str = "Database Agent",
        agent_version: str = "2.0.0",
        dependencies: Optional[List[str]] = None,
    ) -> None:
        # Initialize BaseAgent first
        super().__init__(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_version=agent_version,
            dependencies=dependencies or [],
        )
        
        # Query optimization tracking
        self._query_performance: Dict[str, List[float]] = defaultdict(list)
        self._slow_queries: List[Dict[str, Any]] = []
        self._index_suggestions: List[Dict[str, Any]] = []
        self._query_plan_cache: Dict[str, Dict[str, Any]] = {}
        
        # Sync management tracking
        self._sync_metrics: Dict[str, Any] = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "conflicts_resolved": 0,
            "last_sync_time": None,
            "sync_latency_avg": 0.0,
        }
        
        # Performance monitoring
        self._performance_metrics: Dict[str, Any] = {
            "query_count": 0,
            "query_latency_p95": 0.0,
            "query_latency_p99": 0.0,
            "connection_pool_size": 0,
            "connection_pool_active": 0,
            "connection_pool_idle": 0,
        }
        
        # Performance thresholds (will be set during initialization)
        self._performance_thresholds: Dict[str, float] = {}
        
        # Slow query threshold (default: 100ms)
        self._slow_query_threshold_ms: float = 100.0
        
        # Health check tracking
        self._health_check_history: List[Dict[str, Any]] = []
        
        # Initialize existing components
        # IMPORTANT: Use StorageFacade as the single source of truth for all saves
        from src.infrastructure.database.storage.db import get_storage

        self._storage = get_storage()
        logger.info("✅ StorageFacade initialized (single source of truth)")
        
        # Track initialization state for BaseAgent
        self._components_initialized = False

        # P0-2: Supabase/SQLite connections are READ-ONLY for queries and monitoring
        # ALL WRITES to 'posts' table MUST go through StorageFacade (self._storage)
        # These connections are kept for:
        # - Read-only queries (SELECT)
        # - Monitoring and health checks
        # - Specialized tables (posted_content, posted_metrics) that have complex logic
        try:
            from src.infrastructure.database.manager import SupabaseManager  # lazy import

            self._supabase_manager = SupabaseManager()
            self._supabase = self._supabase_manager.client
            logger.info("✅ Supabase connection initialized (read-only queries & monitoring)")
        except Exception as e:
            logger.warning(f"⚠️ Supabase initialization failed: {e}", exc_info=True)
            self._supabase_manager = None
            self._supabase = None

        # SQLite connection for read-only queries and monitoring
        # NOTE: SQLite writes are handled by StorageFacade async sync queue
        try:
            from src.infrastructure.database.storage.sqlite_adapter import SQLiteAdapter

            self._sqlite = SQLiteAdapter()
            logger.info("✅ SQLite connection initialized (read-only queries & monitoring)")
        except Exception as e:
            logger.warning(f"⚠️ SQLite initialization failed: {e}", exc_info=True)
            self._sqlite = None

        # Duplicate detection (uses storage facade-like logic but scoped here)
        try:
            from src.shared.utils.duplicate_detector import DuplicateDetector

            self._dupes = DuplicateDetector(
                db_manager=None, supabase_manager=self._supabase_manager
            )
            logger.info("✅ Duplicate detector initialized")
        except Exception as e:
            logger.warning(
                f"⚠️ Duplicate detector initialization failed: {e}", exc_info=True
            )
            self._dupes = None

        # Post validation / insertion mapping
        try:
            from src.services.supabase.post_inserter import PostInserter
            from src.shared.utils.post_validator import validate_post

            self._validate_post = validate_post
            duplicate_checker = None
            if self._dupes is not None:

                class DuplicateCheckerWrapper:
                    def __init__(self, detector):
                        self.detector = detector

                    def check_duplicate_post(self, content, author, platform, url=None):
                        item = {
                            "content": content,
                            "author": author,
                            "platform": platform,
                            "url": url,
                        }
                        return self.detector.is_duplicate(item)

                duplicate_checker = DuplicateCheckerWrapper(self._dupes)
            self._post_inserter = (
                PostInserter(self._supabase, duplicate_checker)
                if self._supabase
                else None
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Post inserter initialization failed: {e}", exc_info=True
            )
            self._validate_post = None
            self._post_inserter = None

        # Initialize metrics module (will set record_post_operation callback later)
        try:
            from src.infrastructure.database.metrics import DatabaseMetrics

            self._metrics = DatabaseMetrics(self._supabase, self._sqlite)
            logger.info("✅ Database metrics initialized")
        except Exception as e:
            logger.warning(
                f"⚠️ Database metrics initialization failed: {e}", exc_info=True
            )
            self._metrics = None

        # Initialize repair module
        try:
            from src.infrastructure.database.repair import DatabaseRepair

            self._repair = DatabaseRepair(
                self._supabase, self._sqlite, self._post_inserter
            )
            logger.info("✅ Database repair module initialized")
        except Exception as e:
            logger.warning(
                f"⚠️ Database repair module initialization failed: {e}", exc_info=True
            )
            self._repair = None

        # Initialize validation module
        try:
            from src.infrastructure.database.validation import DatabaseValidation

            self._validation = DatabaseValidation(validate_post_fn=self._validate_post)
            logger.info("✅ Database validation module initialized")
        except Exception as e:
            logger.warning(
                f"⚠️ Database validation module initialization failed: {e}",
                exc_info=True,
            )
            self._validation = None

        # Initialize sync module (will be set up after _normalize_post_data is available)
        self._sync = None

        # Initialize monitoring module
        try:
            from src.infrastructure.database.monitoring import DatabaseMonitoring

            self._monitoring = DatabaseMonitoring(
                get_collection_metrics_fn=self.get_collection_metrics
                if hasattr(self, "get_collection_metrics")
                else None
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            self._monitoring = None

        # Initialize curation module
        try:
            from src.infrastructure.database.curation import DatabaseCuration

            self._curation = DatabaseCuration(supabase=self._supabase)
        except Exception as e:
            logger.error(f"Error: {e}")
            self._curation = None

        # Initialize health/reporting module
        try:
            from src.infrastructure.database.health import DatabaseHealth

            self._health = DatabaseHealth(
                supabase_client=self._supabase,
                sqlite_adapter=self._sqlite,
                get_last_post_id_fn=self.get_last_post_id,
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            self._health = None

        # Mark components as initialized
        self._components_initialized = True

    # --------------- BaseAgent Abstract Methods ---------------
    
    async def initialize(self) -> bool:
        """
        Initialize the database agent.
        
        Sets up all database connections, validates configuration,
        and prepares the agent for execution.
        
        Returns:
            True if initialization was successful, False otherwise
            
        Raises:
            AgentError: If initialization fails
        """
        try:
            self._set_status(AgentStatus.RUNNING)
            
            # Validate connections
            if not self._supabase and not self._sqlite:
                raise AgentError(
                    "No database connections available",
                    agent_id=self.agent_id,
                )
            
            # Test connectivity
            connectivity_ok = await self._test_connectivity()
            if not connectivity_ok:
                raise AgentError(
                    "Database connectivity test failed",
                    agent_id=self.agent_id,
                )
            
            # Initialize query optimization
            await self._initialize_query_optimization()
            
            # Initialize sync management
            await self._initialize_sync_management()
            
            # Initialize performance monitoring
            await self._initialize_performance_monitoring()
            
            # Record initialization metric
            self.record_metric("initialization_success", 1.0)
            
            self._mark_initialized()
            self.publish_event("agent.initialized", {"agent_id": self.agent_id})
            
            logger.info(f"✅ DatabaseAgent {self.agent_id} initialized successfully")
            return True
            
        except Exception as e:
            self._set_status(AgentStatus.ERROR)
            self.metrics["last_error"] = str(e)
            self.record_metric("initialization_failed", 1.0)
            logger.error(f"❌ DatabaseAgent initialization failed: {e}", exc_info=True)
            raise AgentError(
                f"Initialization failed: {e}",
                agent_id=self.agent_id,
            ) from e
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a database task.
        
        Supported task types:
        - "save_post": Save a post to the database
        - "optimize_queries": Run query optimization
        - "sync_databases": Sync SQLite and Supabase
        - "health_check": Perform health check
        - "analyze_performance": Analyze database performance
        - "suggest_indexes": Get index suggestions
        
        Args:
            task: Dictionary containing task data and parameters
                - task_type: Type of task to execute
                - data: Task-specific data
                
        Returns:
            Dictionary containing execution results
            
        Raises:
            AgentError: If task execution fails
        """
        start_time = time.time()
        task_type = task.get("task_type", "unknown")
        
        try:
            self._set_status(AgentStatus.RUNNING)
            
            # Track task execution
            self.record_metric("task_execution", 1.0, tags={"task_type": task_type})
            
            result = {}
            
            if task_type == "save_post":
                post_data = task.get("data", {})
                result = {"success": self.save_post(post_data)}
                
            elif task_type == "optimize_queries":
                result = await self.optimize_queries()
                
            elif task_type == "sync_databases":
                limit = task.get("limit", 100)
                result = await self.sync_databases(limit=limit)
                
            elif task_type == "health_check":
                result = await self.health_check()
                
            elif task_type == "analyze_performance":
                result = await self.analyze_performance()
                
            elif task_type == "suggest_indexes":
                result = await self.suggest_indexes()
                
            else:
                raise AgentError(
                    f"Unknown task type: {task_type}",
                    agent_id=self.agent_id,
                )
            
            # Update execution metrics
            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, success=True)
            
            # Publish task completion event
            self.publish_event(
                "agent.task_completed",
                {
                    "agent_id": self.agent_id,
                    "task_type": task_type,
                    "execution_time": execution_time,
                },
            )
            
            self._set_status(AgentStatus.IDLE)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, success=False)
            self._set_status(AgentStatus.ERROR)
            self.metrics["last_error"] = str(e)
            
            self.publish_event(
                "agent.task_failed",
                {
                    "agent_id": self.agent_id,
                    "task_type": task_type,
                    "error": str(e),
                },
            )
            
            logger.error(f"Task execution failed: {e}", exc_info=True)
            raise AgentError(
                f"Task execution failed: {e}",
                agent_id=self.agent_id,
            ) from e

    # --------------- Query Optimization ---------------
    
    async def _initialize_query_optimization(self) -> None:
        """Initialize query optimization components"""
        try:
            # Set up slow query threshold (default: 100ms)
            self._slow_query_threshold_ms = 100.0
            logger.info("✅ Query optimization initialized")
        except Exception as e:
            logger.warning(f"Query optimization initialization failed: {e}")
    
    async def optimize_queries(self) -> Dict[str, Any]:
        """
        Analyze and optimize database queries.
        
        Returns:
            Dictionary with optimization results including:
            - slow_queries: List of slow queries identified
            - index_suggestions: Suggested indexes
            - query_plans: Query execution plans
        """
        try:
            results = {
                "slow_queries": [],
                "index_suggestions": [],
                "query_plans": {},
                "optimizations_applied": 0,
            }
            
            # Identify slow queries
            slow_queries = await self.identify_slow_queries()
            results["slow_queries"] = slow_queries
            
            # Generate index suggestions
            suggestions = await self.suggest_indexes()
            results["index_suggestions"] = suggestions.get("suggestions", [])
            
            # Analyze query plans for slow queries
            for query_info in slow_queries:
                query = query_info.get("query", "")
                if query:
                    plan = await self.analyze_query_plan(query)
                    if plan:
                        results["query_plans"][query] = plan
            
            # Record metric
            self.record_metric("query_optimization_runs", 1.0)
            
            return results
            
        except Exception as e:
            logger.error(f"Query optimization failed: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def identify_slow_queries(self, threshold_ms: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Identify slow queries based on performance tracking.
        
        Args:
            threshold_ms: Query execution time threshold in milliseconds (default: 100ms)
            
        Returns:
            List of slow query information dictionaries
        """
        threshold = threshold_ms or self._slow_query_threshold_ms
        
        slow_queries = []
        
        # Analyze tracked query performance
        for query_hash, latencies in self._query_performance.items():
            if not latencies:
                continue
                
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else max_latency
            
            # Convert to milliseconds
            avg_ms = avg_latency * 1000
            max_ms = max_latency * 1000
            p95_ms = p95_latency * 1000
            
            if p95_ms > threshold:
                slow_queries.append({
                    "query_hash": query_hash,
                    "avg_latency_ms": avg_ms,
                    "max_latency_ms": max_ms,
                    "p95_latency_ms": p95_ms,
                    "execution_count": len(latencies),
                    "threshold_ms": threshold,
                })
        
        # Sort by p95 latency (worst first)
        slow_queries.sort(key=lambda x: x["p95_latency_ms"], reverse=True)
        
        self._slow_queries = slow_queries
        self.record_metric("slow_queries_identified", len(slow_queries))
        
        return slow_queries
    
    async def suggest_indexes(self) -> Dict[str, Any]:
        """
        Suggest indexes based on query patterns and slow queries.
        
        Returns:
            Dictionary with index suggestions
        """
        suggestions = []
        
        # Analyze slow queries for index opportunities
        for query_info in self._slow_queries:
            query_hash = query_info.get("query_hash", "")
            
            # Common index suggestions based on query patterns
            # This is a simplified version - in production, you'd analyze actual SQL
            if "platform" in query_hash.lower():
                suggestions.append({
                    "table": "posts",
                    "columns": ["platform"],
                    "type": "btree",
                    "reason": "Frequent filtering by platform",
                    "estimated_improvement": "High",
                })
            
            if "created_at" in query_hash.lower():
                suggestions.append({
                    "table": "posts",
                    "columns": ["created_at"],
                    "type": "btree",
                    "reason": "Frequent ordering by created_at",
                    "estimated_improvement": "High",
                })
            
            if "platform" in query_hash.lower() and "created_at" in query_hash.lower():
                suggestions.append({
                    "table": "posts",
                    "columns": ["platform", "created_at"],
                    "type": "btree",
                    "reason": "Composite index for platform + created_at queries",
                    "estimated_improvement": "Very High",
                })
        
        # Remove duplicates
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            key = (suggestion["table"], tuple(suggestion["columns"]))
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)
        
        self._index_suggestions = unique_suggestions
        self.record_metric("index_suggestions_generated", len(unique_suggestions))
        
        return {
            "suggestions": unique_suggestions,
            "count": len(unique_suggestions),
        }
    
    async def analyze_query_plan(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Analyze query execution plan.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Dictionary with query plan information, or None if analysis fails
        """
        try:
            # For Supabase, we can't directly get EXPLAIN plans via the client
            # This is a placeholder that would need to be implemented via RPC or direct SQL
            # For now, we'll return basic analysis
            
            plan = {
                "query": query[:100] + "..." if len(query) > 100 else query,
                "estimated_cost": "N/A",
                "analysis": "Query plan analysis requires direct database access",
                "recommendations": [],
            }
            
            # Cache the plan
            query_hash = str(hash(query))
            self._query_plan_cache[query_hash] = plan
            
            return plan
            
        except Exception as e:
            logger.warning(f"Query plan analysis failed: {e}")
            return None
    
    async def create_index_automatically(
        self, table: str, columns: List[str], index_type: str = "btree"
    ) -> bool:
        """
        Automatically create an index (optional feature).
        
        Args:
            table: Table name
            columns: List of column names
            index_type: Type of index (btree, gin, etc.)
            
        Returns:
            True if index was created, False otherwise
        """
        try:
            # This would require direct SQL execution via Supabase RPC
            # For safety, we'll log the suggestion instead of creating automatically
            logger.info(
                f"Index suggestion: CREATE INDEX ON {table} ({', '.join(columns)})"
            )
            
            # In production, you might want to:
            # 1. Create the index via migration
            # 2. Use Supabase RPC to execute DDL
            # 3. Track created indexes
            
            self.record_metric("index_creation_suggested", 1.0, tags={"table": table})
            return False  # Not automatically creating for safety
            
        except Exception as e:
            logger.error(f"Automatic index creation failed: {e}")
            return False

    # --------------- Sync Management ---------------
    
    async def _initialize_sync_management(self) -> None:
        """Initialize sync management components"""
        try:
            self._ensure_sync_module()
            logger.info("✅ Sync management initialized")
        except Exception as e:
            logger.warning(f"Sync management initialization failed: {e}")
    
    async def sync_databases(self, limit: int = 100) -> Dict[str, Any]:
        """
        Sync SQLite and Supabase databases.
        
        Args:
            limit: Maximum number of records to sync
            
        Returns:
            Dictionary with sync results
        """
        start_time = time.time()
        
        try:
            self._ensure_sync_module()
            
            if not self._sync:
                return {
                    "success": False,
                    "error": "Sync module not available",
                }
            
            # Perform sync
            result = self._sync.retry_failed_syncs(limit=limit)
            
            # Update sync metrics
            sync_time = time.time() - start_time
            self._sync_metrics["total_syncs"] += 1
            self._sync_metrics["successful_syncs"] += result.get("succeeded", 0)
            self._sync_metrics["failed_syncs"] += result.get("failed", 0)
            self._sync_metrics["last_sync_time"] = datetime.utcnow().isoformat()
            
            # Update average latency
            total_syncs = self._sync_metrics["total_syncs"]
            current_avg = self._sync_metrics["sync_latency_avg"]
            self._sync_metrics["sync_latency_avg"] = (
                (current_avg * (total_syncs - 1) + sync_time) / total_syncs
            )
            
            # Record metrics
            self.record_metric("sync_operations", 1.0)
            self.record_metric("sync_latency", sync_time)
            self.record_metric("sync_success_rate", result.get("succeeded", 0) / max(1, result.get("attempted", 1)))
            
            # Publish sync event
            self.publish_event(
                "database.sync_completed",
                {
                    "attempted": result.get("attempted", 0),
                    "succeeded": result.get("succeeded", 0),
                    "failed": result.get("failed", 0),
                    "latency": sync_time,
                },
            )
            
            return {
                "success": True,
                **result,
                "sync_latency": sync_time,
            }
            
        except Exception as e:
            logger.error(f"Database sync failed: {e}", exc_info=True)
            self._sync_metrics["failed_syncs"] += 1
            return {
                "success": False,
                "error": str(e),
            }
    
    async def resolve_sync_conflicts(self) -> Dict[str, Any]:
        """
        Resolve conflicts between SQLite and Supabase.
        
        Returns:
            Dictionary with conflict resolution results
        """
        try:
            # Get sync status
            sync_status = self.get_sync_status_report()
            
            conflicts = []
            resolved = 0
            
            # Identify conflicts (posts that exist in both but differ)
            # This is a simplified version - in production, you'd compare actual data
            unsynced = sync_status.get("unsynced", 0)
            
            if unsynced > 0:
                # For now, we'll use Supabase as the source of truth
                # and sync SQLite to match
                result = await self.sync_databases(limit=unsynced)
                resolved = result.get("succeeded", 0)
            
            self._sync_metrics["conflicts_resolved"] += resolved
            
            self.record_metric("conflicts_resolved", resolved)
            
            return {
                "conflicts_found": len(conflicts),
                "conflicts_resolved": resolved,
                "strategy": "supabase_source_of_truth",
            }
            
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}", exc_info=True)
            return {
                "conflicts_found": 0,
                "conflicts_resolved": 0,
                "error": str(e),
            }
    
    def get_sync_metrics(self) -> Dict[str, Any]:
        """
        Get sync metrics.
        
        Returns:
            Dictionary with sync metrics
        """
        return self._sync_metrics.copy()

    # --------------- Performance Monitoring ---------------
    
    async def _initialize_performance_monitoring(self) -> None:
        """Initialize performance monitoring components"""
        try:
            # Set up performance thresholds
            self._performance_thresholds = {
                "query_latency_p95_ms": 100.0,
                "query_latency_p99_ms": 500.0,
                "sync_latency_ms": 1000.0,
            }
            logger.info("✅ Performance monitoring initialized")
        except Exception as e:
            logger.warning(f"Performance monitoring initialization failed: {e}")
    
    async def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze database performance.
        
        Returns:
            Dictionary with performance analysis results
        """
        try:
            analysis = {
                "query_performance": {},
                "sync_performance": {},
                "connection_pool": {},
                "alerts": [],
            }
            
            # Analyze query performance
            if self._query_performance:
                all_latencies = []
                for latencies in self._query_performance.values():
                    all_latencies.extend(latencies)
                
                if all_latencies:
                    sorted_latencies = sorted(all_latencies)
                    p95_idx = int(len(sorted_latencies) * 0.95)
                    p99_idx = int(len(sorted_latencies) * 0.99)
                    
                    analysis["query_performance"] = {
                        "total_queries": len(all_latencies),
                        "avg_latency_ms": (sum(all_latencies) / len(all_latencies)) * 1000,
                        "p95_latency_ms": sorted_latencies[p95_idx] * 1000,
                        "p99_latency_ms": sorted_latencies[p99_idx] * 1000,
                        "max_latency_ms": max(all_latencies) * 1000,
                    }
                    
                    # Check for performance degradation
                    p95_ms = analysis["query_performance"]["p95_latency_ms"]
                    query_threshold = self._performance_thresholds.get("query_latency_p95_ms", 100.0)
                    if p95_ms > query_threshold:
                        analysis["alerts"].append({
                            "type": "query_performance_degradation",
                            "severity": "warning",
                            "message": f"P95 query latency ({p95_ms:.2f}ms) exceeds threshold",
                            "threshold": query_threshold,
                        })
            
            # Analyze sync performance
            if self._sync_metrics.get("total_syncs", 0) > 0:
                analysis["sync_performance"] = {
                    "total_syncs": self._sync_metrics["total_syncs"],
                    "success_rate": (
                        self._sync_metrics["successful_syncs"]
                        / self._sync_metrics["total_syncs"]
                    ),
                    "avg_latency_ms": self._sync_metrics["sync_latency_avg"] * 1000,
                }
                
                # Check sync latency
                sync_latency_ms = analysis["sync_performance"]["avg_latency_ms"]
                sync_threshold = self._performance_thresholds.get("sync_latency_ms", 1000.0)
                if sync_latency_ms > sync_threshold:
                        analysis["alerts"].append({
                            "type": "sync_performance_degradation",
                            "severity": "warning",
                            "message": f"Average sync latency ({sync_latency_ms:.2f}ms) exceeds threshold",
                            "threshold": sync_threshold,
                        })
            
            # Connection pool status (simplified - would need actual pool monitoring)
            analysis["connection_pool"] = {
                "status": "healthy",
                "note": "Connection pool monitoring requires database-specific implementation",
            }
            
            # Update performance metrics
            if analysis["query_performance"]:
                self._performance_metrics.update({
                    "query_count": analysis["query_performance"].get("total_queries", 0),
                    "query_latency_p95": analysis["query_performance"].get("p95_latency_ms", 0.0),
                    "query_latency_p99": analysis["query_performance"].get("p99_latency_ms", 0.0),
                })
            
            # Publish alerts if any
            if analysis["alerts"]:
                self.publish_event("database.performance_alert", {"alerts": analysis["alerts"]})
            
            self.record_metric("performance_analysis_runs", 1.0)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}", exc_info=True)
            return {"error": str(e)}
    
    def track_query_performance(self, query_hash: str, latency_seconds: float) -> None:
        """
        Track query performance.
        
        Args:
            query_hash: Hash of the query
            latency_seconds: Query execution time in seconds
        """
        # Keep only last 1000 queries per hash
        if len(self._query_performance[query_hash]) >= 1000:
            self._query_performance[query_hash].pop(0)
        
        self._query_performance[query_hash].append(latency_seconds)
        
        # Update metrics
        self._performance_metrics["query_count"] += 1

    # --------------- Health Checks ---------------
    
    async def _test_connectivity(self) -> bool:
        """
        Test database connectivity.
        
        Returns:
            True if connectivity is OK, False otherwise
        """
        try:
            # Test Supabase
            if self._supabase:
                try:
                    # Simple query to test connectivity
                    self._supabase.table("posts").select("id").limit(1).execute()
                except Exception as e:
                    logger.warning(f"Supabase connectivity test failed: {e}")
                    return False
            
            # Test SQLite
            if self._sqlite:
                try:
                    # Simple query to test connectivity
                    if hasattr(self._sqlite, "conn"):
                        cursor = self._sqlite.conn.cursor()
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                except Exception as e:
                    logger.warning(f"SQLite connectivity test failed: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Connectivity test failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Overrides BaseAgent.health_check() to add database-specific checks.
        
        Returns:
            Dictionary with health check results
        """
        # Get base health check
        base_health = await super().health_check()
        
        # Add database-specific health checks
        db_health = {
            **base_health,
            "database_connectivity": {},
            "query_performance": {},
            "sync_status": {},
            "resource_usage": {},
        }
        
        # Check database connectivity
        connectivity_ok = await self._test_connectivity()
        db_health["database_connectivity"] = {
            "supabase": self._supabase is not None,
            "sqlite": self._sqlite is not None,
            "overall": connectivity_ok,
        }
        
        # Check query performance
        if self._query_performance:
            all_latencies = []
            for latencies in self._query_performance.values():
                all_latencies.extend(latencies[-100:])  # Last 100 queries
            
            if all_latencies:
                sorted_latencies = sorted(all_latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                
                db_health["query_performance"] = {
                    "p95_latency_ms": sorted_latencies[p95_idx] * 1000,
                    "avg_latency_ms": (sum(all_latencies) / len(all_latencies)) * 1000,
                    "query_count": len(all_latencies),
                    "healthy": sorted_latencies[p95_idx] * 1000 < 100.0,
                }
        
        # Check sync status
        sync_status = self.get_sync_status_report()
        if sync_status:
            db_health["sync_status"] = {
                "synced_percentage": sync_status.get("sync_percentage", 0.0),
                "unsynced_count": sync_status.get("unsynced", 0),
                "healthy": sync_status.get("sync_percentage", 0.0) > 95.0,
            }
        else:
            db_health["sync_status"] = {
                "synced_percentage": 0.0,
                "unsynced_count": 0,
                "healthy": False,
            }
        
        # Resource usage (simplified)
        db_health["resource_usage"] = {
            "query_cache_size": len(self._query_plan_cache),
            "performance_tracking_size": sum(len(v) for v in self._query_performance.values()),
            "status": "normal",
        }
        
        # Update overall health
        db_health["healthy"] = (
            base_health.get("healthy", False)
            and connectivity_ok
            and db_health["query_performance"].get("healthy", True)
            and db_health["sync_status"].get("healthy", True)
        )
        
        # Store health check history
        self._health_check_history.append({
            "timestamp": time.time(),
            "health": db_health,
        })
        
        # Keep only last 100 health checks
        if len(self._health_check_history) > 100:
            self._health_check_history.pop(0)
        
        return db_health

    # --------------- Metrics / Freshness ---------------
    # Delegated to metrics module for better organization
    def ensure_metrics_table(self) -> None:
        """Ensure local cache has the metrics table. Supabase handled via migration."""
        if self._metrics:
            self._metrics.ensure_metrics_table()

    def get_collection_metrics(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get collection metrics for a platform"""
        if self._metrics:
            return self._metrics.get_collection_metrics(platform)
        # Fallback implementation
        if self._supabase is not None:
            try:
                r = (
                    self._supabase.table("collection_metrics")
                    .select("*")
                    .eq("platform", platform)
                    .limit(1)
                    .execute()
                )
                if getattr(r, "data", None):
                    return r.data[0]
            except Exception as e:
                logger.error(f"Error: {e}")
        return None

    def record_post_operation(
        self,
        post_id: str,
        platform: str,
        operation: str = "insert",
        quality_score: Optional[float] = None,
        value_score: Optional[float] = None,
        has_analysis: bool = False,
    ) -> bool:
        """Track individual post operations (insert/update) for monitoring"""
        if self._metrics:
            return self._metrics.record_post_operation(
                post_id, platform, operation, quality_score, value_score, has_analysis
            )
        return False

    def record_collection_result(
        self,
        platform: str,
        count: int,
        success: bool = True,
        failure_reason: Optional[str] = None,
        *,
        started_at: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_details: Optional[str] = None,
    ) -> bool:
        """Record collection result for a platform"""
        if self._metrics:
            return self._metrics.record_collection_result(
                platform,
                count,
                success,
                failure_reason,
                started_at=started_at,
                duration_seconds=duration_seconds,
                message=message,
                metadata=metadata,
                error_details=error_details,
            )
        return False

    # --------------- Completeness / Repair ---------------
    # Delegated to repair module for better organization
    def _is_empty(self, v: Any) -> bool:
        """Check if a value is empty"""
        if self._repair:
            return self._repair._is_empty(v)
        # Fallback implementation
        try:
            if v is None:
                return True
            if isinstance(v, str) and not v.strip():
                return True
            if isinstance(v, (list, dict)) and not v:
                return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        return False

    def count_incomplete_posts(self) -> int:
        """Count posts in Supabase missing required fields."""
        if self._repair:
            return self._repair.count_incomplete_posts()
        return 0

    def repair_incomplete_posts(self, limit: int = 200) -> int:
        """Fetch incomplete posts and backfill required fields with safe defaults."""
        if self._repair:
            return self._repair.repair_incomplete_posts(limit)
        return 0

    def _infer_platform(self, post: Dict[str, Any]) -> Optional[str]:
        """Infer platform from post data"""
        if self._repair:
            return self._repair._infer_platform(post)
        return None

    def fix_invalid_platforms(
        self,
        *,
        limit: int = 2000,
        dry_run: bool = True,
        auto: bool = False,
        interval_minutes: int = 720,
    ) -> Dict[str, Any]:
        """Normalize posts with invalid or blank platform values."""
        if self._repair:
            return self._repair.fix_invalid_platforms(
                limit=limit,
                dry_run=dry_run,
                auto=auto,
                interval_minutes=interval_minutes,
            )
        return {"updated": 0, "skipped": True, "reason": "Repair module not available"}

    # --------------- Monitoring ---------------
    # Delegated to monitoring module for better organization
    def detect_stale_collections(
        self, thresholds_minutes: Optional[Dict[str, int]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Detect stale collections based on last run time"""
        if self._monitoring:
            return self._monitoring.detect_stale_collections(thresholds_minutes)
        return {}

    def notify_stale(self, stale: Dict[str, Dict[str, Any]]) -> None:
        """Notify about stale collections"""
        if self._monitoring:
            self._monitoring.notify_stale(stale)

    async def trigger_collections(self, platforms: List[str]) -> Dict[str, int]:
        from src.application.automation.orchestrator import Orchestrator

        results: Dict[str, int] = {}
        orch = Orchestrator()
        for p in platforms:
            try:
                cnt = await orch.collect_platform(p)
                results[p] = cnt
                self.record_collection_result(p, cnt, success=True)
            except Exception as e:
                logger.error(f"Error: {e}")
                self.record_collection_result(
                    p, 0, success=False, failure_reason=str(e)[:200]
                )
                results[p] = 0
        return results

    # --------------- Proactive DBA Functions ---------------
    # Delegated to validation module for better organization
    def validate_and_monitor_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Validate, check quality, and monitor every post"""
        if self._validation:
            # Set record_post_operation callback dynamically
            if not self._validation._record_post_operation_set:
                self._validation._record_post_operation = self.record_post_operation
                self._validation._record_post_operation_set = True
            return self._validation.validate_and_monitor_post(post)
        # Fallback to empty result if validation module not available
        return {
            "validated": False,
            "quality_checked": False,
            "issues_found": [],
            "warnings": [],
            "monitored": False,
        }

    # --------------- Core Operations ---------------
    # Delegated to validation module for better organization
    def _normalize_post_data(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and clean post data BEFORE validation"""
        if self._validation:
            return self._validation.normalize_post_data(post)
        # Fallback: return post as-is if validation module not available
        return post

    def _ensure_sync_module(self):
        """Ensure sync module is initialized with proper callbacks"""
        if self._sync is None:
            try:
                from src.infrastructure.database.sync import DatabaseSync

                self._sync = DatabaseSync(
                    supabase=self._supabase,
                    sqlite=self._sqlite,
                    post_inserter=self._post_inserter,
                    normalize_post_data_fn=self._normalize_post_data,
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Database sync module initialization failed: {e}", exc_info=True
                )
                self._sync = None

    def save_post(
        self, post: Dict[str, Any], retries: int = 3, backoff_seconds: float = 1.5
    ) -> bool:
        """
        Save a post - DELEGATES TO StorageFacade (single source of truth).
        - NORMALIZES and cleans data FIRST (prevents corruption)
        - Delegates to StorageFacade.save_post() for actual save
        - Adds monitoring/validation on top
        - Ensures post_id is set using PostIDGenerator
        """
        hub = get_observability_hub()
        post_id = post.get("post_id", "unknown")
        platform = post.get("platform", "unknown")

        # Track metrics
        hub.metrics.increment(
            "database_agent.save_post.called", labels={"platform": platform}
        )

        try:
            # Sanity
            if not isinstance(post, dict):
                logger.error("save_post: invalid post type")
                return False

            # CRITICAL: Normalize and clean data FIRST (this prevents all the corruption issues)
            post = self._normalize_post_data(post)

            # Ensure post_id is set (use ID generator)
            if not post.get("post_id"):
                from src.infrastructure.database.storage.id_generator import PostIDGenerator

                post["post_id"] = PostIDGenerator.generate_post_id(post)
            else:
                # Normalize existing post_id
                from src.infrastructure.database.storage.id_generator import PostIDGenerator

                platform = post.get("platform", "")
                post["post_id"] = PostIDGenerator._normalize_id(
                    str(post["post_id"]), platform
                )

            # DELEGATE TO StorageFacade (single source of truth)
            # StorageFacade handles: duplicate checks, SQLite + Supabase sync, collected_at
            result = self._storage.save_post(post)

            post_id = post.get("post_id", post_id)
            platform = post.get("platform", platform)

            # Track success
            if result:
                hub.metrics.increment(
                    "database_agent.save_post.success", labels={"platform": platform}
                )
            else:
                hub.metrics.increment(
                    "database_agent.save_post.failed",
                    labels={
                        "platform": platform,
                        "reason": "storage_facade_returned_false",
                    },
                )

            # P0-2: Monitoring - read-only query to verify sync status
            # This is acceptable as it's monitoring, not a write operation
            if result and post_id and self._sqlite:
                try:
                    # Check if synced to Supabase by querying Supabase (read-only)
                    if self._supabase:
                        try:
                            existing = (
                                self._supabase.table("posts")
                                .select("post_id")
                                .eq("platform", platform)
                                .eq("post_id", post_id)
                                .limit(1)
                                .execute()
                            )
                            if existing.data:
                                self._sqlite.mark_synced_to_supabase(
                                    post_id, synced=True
                                )
                            else:
                                self._sqlite.mark_synced_to_supabase(
                                    post_id, synced=False, error="Not found in Supabase"
                                )
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            pass  # Don't fail if monitoring fails
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass  # Don't fail if monitoring fails

            # AUTOMATIC CURATION: Check if post should be in usable_posts (only if saved successfully)
            if result:
                has_analysis = bool(
                    post.get("analyzed_at")
                    and post.get("ai_summary")
                    and len(str(post.get("ai_summary", "")).strip()) >= 30
                )

                if has_analysis:
                    try:
                        curated = False
                        if self._curation:
                            curated = self._curation.auto_curate_to_usable_posts(post)
                        if curated:
                            logger.info(
                                f"✅ Auto-curated post {post_id} ({platform}) to usable_posts"
                            )
                        else:
                            logger.debug(
                                f"Post {post_id} did not meet usable_posts criteria"
                            )
                    except Exception as e:
                        # Don't fail save_post if auto-curation fails - log and continue
                        logger.warning(f"Auto-curation failed for post {post_id}: {e}")
                        import traceback

                        logger.debug(traceback.format_exc())

            return result

        except Exception as e:
            logger.error(f"DB Agent save_post error: {e}")
            import traceback

            logger.debug(traceback.format_exc())

            # Track error
            hub.metrics.increment(
                "database_agent.save_post.error",
                labels={"platform": platform, "error_type": type(e).__name__},
            )
            hub.errors.capture_exception(
                e,
                context={
                    "operation": "save_post",
                    "post_id": post_id,
                    "platform": platform,
                },
            )

            return False

    def get_last_post_id(self, platform: str) -> Optional[str]:
        """
        Fetch the most recent post_id for a platform from Supabase.
        Returns normalized Reddit IDs with t3_ prefix if platform == 'reddit'.
        """
        if not self._supabase:
            return None
        try:
            r = (
                self._supabase.table("posts")
                .select("post_id")
                .eq("platform", platform)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if getattr(r, "data", None):
                pid = (r.data[0].get("post_id") or "").strip()
                if platform == "reddit" and pid and not pid.startswith("t3_"):
                    pid = f"t3_{pid}"
                return pid or None
        except Exception as e:
            logger.debug(f"get_last_post_id failed for {platform}: {e}")
            return None
        return None

    # --------------- Health / Maintenance ---------------
    def health_report(self) -> Dict[str, Any]:
        """Return a quick health summary for DB components."""
        if getattr(self, "_health", None):
            return self._health.health_report()
        return {
            "supabase_ok": False,
            "sqlite_ok": False,
            "latest_ids": {"twitter": None, "reddit": None, "threads": None},
            "sync_status": {},
            "generated_at": datetime.utcnow().isoformat(),
        }

    # --------------- Sync Operations ---------------
    # Delegated to sync module for better organization
    def retry_failed_syncs(self, limit: int = 100) -> Dict[str, Any]:
        """Retry syncing unsynced posts from SQLite to Supabase"""
        self._ensure_sync_module()
        if self._sync:
            return self._sync.retry_failed_syncs(limit)
        return {"attempted": 0, "succeeded": 0, "failed": 0, "errors": []}

    def get_sync_status_report(self) -> Dict[str, Any]:
        """Get detailed sync status report for visibility"""
        if self._sync:
            return self._sync.get_sync_status_report()
            return {
                "error": "Sync module not available",
                "total": 0,
                "synced": 0,
                "unsynced": 0,
                "failed": 0,
                "sync_percentage": 0.0,
            }

    def recent_activity(self, minutes: int = 60) -> Dict[str, int]:
        """Counts posts created in the last N minutes (Supabase)."""
        if getattr(self, "_health", None):
            return self._health.recent_activity(minutes)
        return {"twitter": 0, "reddit": 0, "threads": 0}

    # --------------- Posted Performance APIs ---------------
    def _get_posted_content_id(
        self, platform: str, platform_post_id: str
    ) -> Optional[int]:
        if not self._supabase:
            return None
        try:
            r = (
                self._supabase.table("posted_content")
                .select("id")
                .eq("platform", platform)
                .eq("platform_post_id", platform_post_id)
                .limit(1)
                .execute()
            )
            if getattr(r, "data", None):
                return int(r.data[0]["id"])
        except Exception as e:
            logger.debug(
                f"_get_posted_content_id failed for {platform}/{platform_post_id}: {e}"
            )
            return None
        return None

    def record_post_publication(
        self,
        platform: str,
        platform_post_id: str,
        *,
        url: str = "",
        persona: str = "",
        content_hash: str = "",
        posted_at: Optional[str] = None,
        initial_text: str = "",
        topic: str = "",
        tags: Optional[List[str]] = None,
        has_media: bool = False,
        lang: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Record post publication - delegates to StorageFacade for posted_content table.
        NOTE: This is a specialized table (not 'posts'), so direct write is acceptable
        but we prefer StorageFacade when possible.
        """
        # P0-2: Try StorageFacade first (if it supports posted_content)
        try:
            row = {
                "platform": platform,
                "platform_post_id": platform_post_id,
                "url": url,
                "persona": persona,
                "content_hash": content_hash,
                "posted_at": posted_at or datetime.utcnow().isoformat(),
                "initial_text": initial_text,
                "topic": topic,
                "tags": tags or [],
                "has_media": bool(has_media),
                "lang": lang,
            }
            # Delegate to StorageFacade (it has save_posted_content method)
            result = self._storage.save_posted_content(row)
            if result:
                # Return the row as dict (StorageFacade doesn't return the created record)
                # For now, we'll query it back if needed
                return row
        except Exception as e:
            logger.debug(f"StorageFacade.save_posted_content failed, using direct write: {e}")
        
        # Fallback: Direct write (for backward compatibility)
        if not self._supabase:
            return None
        try:
            r = (
                self._supabase.table("posted_content")
                .upsert(row, on_conflict="platform,platform_post_id")
                .execute()
            )
            if getattr(r, "data", None):
                return r.data[0]
        except Exception as e:
            logger.warning(
                f"record_post_publication failed for {platform}/{platform_post_id}: {e}"
            )
            return None
        return None

    def _compute_engagement_score(
        self, views: int, likes: int, comments: int, shares: int, bookmarks: int
    ) -> float:
        try:
            num = likes + 2 * comments + 3 * shares + 2 * bookmarks
            den = max(1, views)
            return float(num) / float(den)
        except Exception as e:
            logger.debug(f"_compute_engagement_score failed: {e}")
            return 0.0

    def upsert_posted_metrics(
        self,
        platform: str,
        platform_post_id: str,
        snapshot: Dict[str, Any],
    ) -> bool:
        if not self._supabase:
            return False
        try:
            pc_id = self._get_posted_content_id(platform, platform_post_id)
            if not pc_id:
                # Create shell row if missing
                created = self.record_post_publication(platform, platform_post_id)
                pc_id = int(created["id"]) if created and created.get("id") else None
                if not pc_id:
                    return False

            snap_at = snapshot.get("snapshot_at") or datetime.utcnow().isoformat()
            row = {
                "posted_content_id": pc_id,
                "snapshot_at": snap_at,
                "views": int(snapshot.get("views") or 0),
                "likes": int(snapshot.get("likes") or 0),
                "comments": int(snapshot.get("comments") or 0),
                "shares": int(snapshot.get("shares") or 0),
                "bookmarks": int(snapshot.get("bookmarks") or 0),
            }
            # Upsert by unique key (posted_content_id, snapshot_at) is not supported directly → emulate
            self._supabase.table("posted_metrics").upsert(
                row, on_conflict="posted_content_id,snapshot_at"
            ).execute()

            # Recompute aggregates on posted_content
            agg = self._supabase.rpc(
                "exec",
                {
                    "sql": f"select coalesce(sum(views),0) v, coalesce(sum(likes),0) l, coalesce(sum(comments),0) c, coalesce(sum(shares),0) s, coalesce(sum(bookmarks),0) b from posted_metrics where posted_content_id={pc_id}"
                },
            )
            # Fallback if RPC not available: fetch and sum in client
            if not getattr(agg, "data", None):
                res = (
                    self._supabase.table("posted_metrics")
                    .select("views,likes,comments,shares,bookmarks")
                    .eq("posted_content_id", pc_id)
                    .execute()
                )
                v = l = c = s = b = 0
                for r in res.data or []:
                    v += int(r.get("views") or 0)
                    l += int(r.get("likes") or 0)
                    c += int(r.get("comments") or 0)
                    s += int(r.get("shares") or 0)
                    b += int(r.get("bookmarks") or 0)
            else:
                d0 = (
                    agg.data[0] if isinstance(agg.data, list) and agg.data else agg.data
                )
                v = int(d0.get("v") or 0)
                l = int(d0.get("l") or 0)
                c = int(d0.get("c") or 0)
                s = int(d0.get("s") or 0)
                b = int(d0.get("b") or 0)

            escore = self._compute_engagement_score(v, l, c, s, b)
            self._supabase.table("posted_content").update(
                {
                    "total_views": v,
                    "total_likes": l,
                    "total_comments": c,
                    "total_shares": s,
                    "total_bookmarks": b,
                    "engagement_score": escore,
                }
            ).eq("id", pc_id).execute()
            return True
        except Exception as e:
            logger.warning(
                f"upsert_posted_metrics failed for {platform}/{platform_post_id}: {e}"
            )
            return False

    def get_top_posts(
        self,
        since_minutes: int = 10080,
        limit: int = 20,
        platform: Optional[str] = None,
        persona: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._supabase:
            return []
        try:
            q = (
                self._supabase.table("posted_content")
                .select("*")
                .gt(
                    "posted_at",
                    (
                        datetime.utcnow() - timedelta(minutes=max(1, since_minutes))
                    ).isoformat(),
                )
                .order("engagement_score", desc=True)
                .limit(max(1, min(100, limit)))
            )
            if platform:
                q = q.eq("platform", platform)
            if persona:
                q = q.eq("persona", persona)
            r = q.execute()
            return getattr(r, "data", []) or []
        except Exception as e:
            logger.debug(f"get_top_posts failed: {e}")
            return []

    # --------------- Quality Metrics ---------------
    # Delegated to metrics module for better organization
    def get_quality_metrics(
        self,
        platform: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Get quality metrics for monitoring and reporting"""
        if self._metrics:
            return self._metrics.get_quality_metrics(platform, hours, limit)
            return {
                "avg_quality": 0.0,
                "avg_value": 0.0,
                "count": 0,
                "low_quality_count": 0,
            }

    def get_quality_trends(
        self,
        platform: Optional[str] = None,
        days: int = 7,
    ) -> Dict[str, list]:
        """Get quality score trends over time"""
        if self._metrics:
            return self._metrics.get_quality_trends(platform, days)
            return {"quality": [], "value": [], "timestamps": []}

    def backfill_quality_metrics(self, limit: int = 1000) -> int:
        """Backfill quality metrics for existing posts"""
        if self._metrics:
            # Set callback to self.record_post_operation for backfill
            if not self._metrics._record_post_operation_set:
                self._metrics._record_post_operation = self.record_post_operation
                self._metrics._record_post_operation_set = True
            return self._metrics.backfill_quality_metrics(limit)
            return 0

    def audit_database(
        self, limit: int = 100, platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Proactive DBA function: Audit database for issues.
        Like a human DBA would do - check everything.

        Returns:
            Dict with audit results, issues found, and recommendations
        """
        results = {
            "posts_checked": 0,
            "issues_found": [],
            "warnings": [],
            "critical_issues": [],
            "recommendations": [],
        }

        try:
            # Get recent posts to audit
            if self._supabase:
                query = (
                    self._supabase.table("posts")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                )

                if platforms:
                    query = query.in_("platform", platforms)

                result = query.execute()
                posts = getattr(result, "data", []) or []
            elif self._sqlite:
                # Fallback to SQLite
                posts = self._sqlite.get_posts(limit=limit)
            else:
                return results

            results["posts_checked"] = len(posts)

            # Audit each post
            for post in posts:
                # Validate and check quality
                audit_result = self.validate_and_monitor_post(post)

                if audit_result.get("issues_found"):
                    results["issues_found"].extend(audit_result["issues_found"])

                    # Categorize issues
                    critical = [
                        issue
                        for issue in audit_result["issues_found"]
                        if any(
                            keyword in issue.lower()
                            for keyword in [
                                "missing",
                                "invalid",
                                "failed",
                                "impossible",
                                "error",
                            ]
                        )
                    ]
                    if critical:
                        results["critical_issues"].append(
                            {
                                "post_id": post.get("post_id"),
                                "platform": post.get("platform"),
                                "issues": critical,
                            }
                        )

                if audit_result.get("warnings"):
                    results["warnings"].extend(audit_result["warnings"])

            # Generate recommendations
            if results["critical_issues"]:
                results["recommendations"].append(
                    f"Found {len(results['critical_issues'])} posts with critical issues. Review and fix them."
                )

            if len(results["issues_found"]) > len(posts) * 0.3:
                results["recommendations"].append(
                    f"High issue rate ({len(results['issues_found'])}/{len(posts)}). Review collection process."
                )

            # Check for common patterns
            placeholder_count = sum(
                1
                for post in posts
                if any(
                    placeholder in (post.get("content", "") or "").lower()
                    for placeholder in [
                        "scraping failed",
                        "extraction failed",
                        "placeholder",
                    ]
                )
            )
            if placeholder_count > 0:
                results["recommendations"].append(
                    f"Found {placeholder_count} posts with placeholder content. Check extractors."
                )

            truncated_count = sum(
                1 for post in posts if (post.get("content", "") or "").endswith("...")
            )
            if truncated_count > 0:
                results["recommendations"].append(
                    f"Found {truncated_count} posts with truncated content. Check extractors."
                )

        except Exception as e:
            logger.error(f"DB Agent audit_database failed: {e}")

        return results

    def check_recent_posts_quality(
        self, hours: int = 24, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Check quality of recently collected posts.
        Like a DBA monitoring recent activity.
        """
        results = {
            "posts_checked": 0,
            "quality_issues": [],
            "collection_issues": [],
            "integrity_issues": [],
        }

        try:
            since = (datetime.utcnow() - timedelta(hours=max(1, hours))).isoformat()

            if self._supabase:
                query = (
                    self._supabase.table("posts")
                    .select("*")
                    .gt("created_at", since)
                    .order("created_at", desc=True)
                    .limit(limit)
                )
                result = query.execute()
                posts = getattr(result, "data", []) or []
            else:
                return results

            results["posts_checked"] = len(posts)

            for post in posts:
                # Check data quality
                quality_issues = self._check_data_quality(post)
                if quality_issues:
                    results["quality_issues"].append(
                        {
                            "post_id": post.get("post_id"),
                            "platform": post.get("platform"),
                            "issues": quality_issues,
                        }
                    )

                # Check collection issues
                collection_issues = self._check_collection_issues(post)
                if collection_issues:
                    results["collection_issues"].append(
                        {
                            "post_id": post.get("post_id"),
                            "platform": post.get("platform"),
                            "issues": collection_issues,
                        }
                    )

                # Check integrity
                integrity_issues = self._check_data_integrity(post)
                if integrity_issues:
                    results["integrity_issues"].append(
                        {
                            "post_id": post.get("post_id"),
                            "platform": post.get("platform"),
                            "issues": integrity_issues,
                        }
                    )

        except Exception as e:
            logger.error(f"DB Agent check_recent_posts_quality failed: {e}")

        return results

    def cleanup_bad_posts(
        self,
        limit: int = 1000,
        platforms: Optional[List[str]] = None,
        min_issues: int = 2,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Cleanup wrongly collected posts.
        Like a DBA cleaning up bad data.

        Args:
            limit: Maximum number of posts to check
            platforms: Filter by platforms (None = all)
            min_issues: Minimum number of issues to consider a post "bad"
            dry_run: If True, only report issues without deleting

        Returns:
            Dict with cleanup results
        """
        results = {
            "posts_checked": 0,
            "bad_posts_found": 0,
            "posts_deleted": 0,
            "posts_failed": 0,
            "bad_posts": [],
            "errors": [],
        }

        try:
            # Get all posts to check
            if self._supabase:
                query = (
                    self._supabase.table("posts")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                )

                if platforms:
                    query = query.in_("platform", platforms)

                result = query.execute()
                posts = getattr(result, "data", []) or []
            elif self._sqlite:
                posts = self._sqlite.get_posts(limit=limit)
            else:
                return results

            results["posts_checked"] = len(posts)

            # Check each post
            for post in posts:
                # Validate and check for issues
                audit_result = self.validate_and_monitor_post(post)
                issues = audit_result.get("issues_found", [])

                # Check if post is "bad" (has critical issues)
                # BE CONSERVATIVE: Only delete clearly broken posts
                is_bad = False
                critical_keywords = [
                    "placeholder",
                    "truncated",
                    "missing",
                    "invalid",
                    "failed",
                    "error",
                    "impossible",
                    "scraping failed",
                    "extraction failed",
                ]

                # Count critical issues (excluding Reddit post_id format warnings - those might be false positives)
                critical_issues = [
                    issue
                    for issue in issues
                    if any(keyword in issue.lower() for keyword in critical_keywords)
                    and "reddit post_id" not in issue.lower()
                ]  # Exclude Reddit post_id format warnings

                # Also check for placeholder content directly (MOST IMPORTANT)
                content = post.get("content", "")
                if content:
                    content_lower = content.lower()
                    # Only flag if content is clearly a placeholder/error
                    if any(
                        placeholder in content_lower
                        for placeholder in [
                            "scraping failed",
                            "extraction failed",
                            "content extraction in progress",
                            "post from",
                            "placeholder",
                            "error extracting",
                        ]
                    ):
                        is_bad = True

                # Check for truncated content (ends with ...) - but be careful, some posts legitimately end with ...
                # Only flag if content is very short and ends with ...
                if content and len(content) < 50 and content.endswith("..."):
                    is_bad = True

                # Check for missing essential fields (MOST IMPORTANT)
                # Only delete if BOTH author AND url are missing/invalid
                has_valid_author = post.get("author") and post.get(
                    "author", ""
                ).lower() not in ["unknown", "n/a", ""]
                has_valid_url = post.get("url") and post.get("url", "").startswith(
                    "http"
                )

                if not has_valid_author and not has_valid_url:
                    is_bad = True  # Both missing = definitely bad
                elif not has_valid_author and not content:
                    is_bad = True  # No author and no content = bad

                # If has enough critical issues (excluding Reddit format warnings), mark as bad
                if len(critical_issues) >= min_issues:
                    is_bad = True

                if is_bad:
                    results["bad_posts_found"] += 1
                    results["bad_posts"].append(
                        {
                            "id": post.get("id"),
                            "post_id": post.get("post_id"),
                            "platform": post.get("platform"),
                            "author": post.get("author"),
                            "content_preview": (content or "")[:100],
                            "issues": issues,
                            "critical_issues": critical_issues,
                        }
                    )

                    # Delete if not dry run
                    if not dry_run:
                        try:
                            # Delete from Supabase
                            if self._supabase and post.get("id"):
                                self._supabase.table("posts").delete().eq(
                                    "id", post.get("id")
                                ).execute()

                            # Delete from SQLite
                            if self._sqlite and post.get("post_id"):
                                try:
                                    cur = self._sqlite.conn.cursor()
                                    cur.execute(
                                        "DELETE FROM posts WHERE post_id = ?",
                                        (post.get("post_id"),),
                                    )
                                    self._sqlite.conn.commit()
                                except Exception as e:
                                    logger.error(f"Error: {e}")

                            results["posts_deleted"] += 1
                            logger.info(
                                f"🗑️ Deleted bad post: {post.get('post_id')} ({post.get('platform')})"
                            )
                        except Exception as e:
                            results["posts_failed"] += 1
                            results["errors"].append(
                                f"Failed to delete {post.get('post_id')}: {e}"
                            )
                            logger.error(
                                f"Failed to delete post {post.get('post_id')}: {e}"
                            )

        except Exception as e:
            logger.error(f"DB Agent cleanup_bad_posts failed: {e}")
            results["errors"].append(str(e))

        return results

    def get_performance_cohorts(self, window_minutes: int = 10080) -> Dict[str, Any]:
        # Simple client-side cohorts by buckets
        items = self.get_top_posts(since_minutes=window_minutes, limit=500)
        cohorts: Dict[str, Dict[str, Any]] = {
            "platform": {},
            "persona": {},
            "has_media": {"true": {"n": 0, "avg": 0.0}, "false": {"n": 0, "avg": 0.0}},
        }

        def add(bucket: Dict[str, Any], key: str, esc: float):
            if key not in bucket:
                bucket[key] = {"n": 0, "avg": 0.0}
            b = bucket[key]
            n = b["n"] + 1
            b["avg"] = (b["avg"] * b["n"] + esc) / n
            b["n"] = n

        for it in items:
            esc = float(it.get("engagement_score") or 0)
            add(cohorts["platform"], str(it.get("platform")), esc)
            add(cohorts["persona"], str(it.get("persona")), esc)
            add(cohorts["has_media"], "true" if it.get("has_media") else "false", esc)
        return cohorts

    # --------------- ID Format Checks ---------------
    def id_format_report(self, sample_limit: int = 1000) -> Dict[str, Any]:
        """Report on ID format issues per platform (e.g., Reddit t3_ prefix)."""
        if getattr(self, "_health", None):
            return self._health.id_format_report(sample_limit)
        return {
            "reddit": {"bad": 0, "checked": 0},
            "twitter": {"bad": 0, "checked": 0},
            "threads": {"bad": 0, "checked": 0},
        }

    # --------------- Curation ---------------
    # Delegated to curation module for better organization
    def auto_curate_to_usable_posts(self, post: Dict[str, Any]) -> bool:
        """Automatically curate post to usable_posts table if it meets criteria"""
        if self._curation:
            return self._curation.auto_curate_to_usable_posts(post)
        return False

    # --------------- Publishing Table Methods ---------------
    # All publishing table operations delegate to StorageFacade (single source of truth)

    def save_transformation(self, transformation: Dict[str, Any]) -> bool:
        """Save a rewrite transformation - delegates to StorageFacade"""
        return self._storage.save_transformation(transformation)

    def save_scheduled_post(self, scheduled: Dict[str, Any]) -> bool:
        """Save a scheduled post - delegates to StorageFacade"""
        return self._storage.save_scheduled_post(scheduled)

    def update_scheduled_post(self, scheduled_id: int, updates: Dict[str, Any]) -> bool:
        """Update a scheduled post - delegates to StorageFacade"""
        return self._storage.update_scheduled_post(scheduled_id, updates)

    def save_posted_content(self, posted: Dict[str, Any]) -> bool:
        """Save posted content record - delegates to StorageFacade"""
        return self._storage.save_posted_content(posted)

    def save_rewrite_feedback(self, feedback: Dict[str, Any]) -> bool:
        """Save rewrite feedback - delegates to StorageFacade"""
        return self._storage.save_rewrite_feedback(feedback)
