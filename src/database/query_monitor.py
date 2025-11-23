#!/usr/bin/env python3
"""
Database Query Performance Monitor
==================================
Monitors and logs slow database queries for performance optimization
Created: 2025-11-20
Priority: P2 - Query performance monitoring

Usage:
    from src.infrastructure.database.query_monitor import monitor_query, get_slow_queries
    
    @monitor_query
    def my_query_function():
        # Your database query
        pass
"""

import functools
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)

# Global query statistics
_query_stats: Dict[str, List[float]] = defaultdict(list)
_slow_queries: List[Dict[str, Any]] = []
_query_patterns: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    'count': 0,
    'total_time_ms': 0.0,
    'min_time_ms': float('inf'),
    'max_time_ms': 0.0,
    'errors': 0,
})

# Configuration
SLOW_QUERY_THRESHOLD_MS = 100  # Log queries slower than 100ms
MAX_SLOW_QUERIES = 1000  # Maximum number of slow queries to keep in memory


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_name: str
    execution_time_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    query_type: str = "unknown"
    row_count: Optional[int] = None
    error: Optional[str] = None


def monitor_query(
    threshold_ms: float = SLOW_QUERY_THRESHOLD_MS,
    query_type: str = "unknown"
):
    """
    Decorator to monitor query performance
    
    Args:
        threshold_ms: Minimum execution time (ms) to log as slow query
        query_type: Type of query (e.g., 'select', 'insert', 'update')
    
    Example:
        @monitor_query(threshold_ms=50, query_type='select')
        def get_posts():
            return db.query("SELECT * FROM posts")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            query_name = f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                
                # Calculate execution time
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Track statistics
                _query_stats[query_name].append(execution_time_ms)
                
                # Track query patterns
                pattern = query_name.split('.')[-1]  # Just function name
                _query_patterns[pattern]['count'] += 1
                _query_patterns[pattern]['total_time_ms'] += execution_time_ms
                _query_patterns[pattern]['min_time_ms'] = min(
                    _query_patterns[pattern]['min_time_ms'], execution_time_ms
                )
                _query_patterns[pattern]['max_time_ms'] = max(
                    _query_patterns[pattern]['max_time_ms'], execution_time_ms
                )
                
                # Check if slow query
                if execution_time_ms > threshold_ms:
                    row_count = None
                    if isinstance(result, (list, tuple)):
                        row_count = len(result)
                    elif hasattr(result, 'count'):
                        row_count = result.count
                    
                    metrics = QueryMetrics(
                        query_name=query_name,
                        execution_time_ms=execution_time_ms,
                        query_type=query_type,
                        row_count=row_count,
                    )
                    
                    slow_query_entry = {
                        'name': query_name,
                        'time_ms': execution_time_ms,
                        'timestamp': metrics.timestamp.isoformat(),
                        'type': query_type,
                        'row_count': row_count,
                    }
                    
                    _slow_queries.append(slow_query_entry)
                    
                    # Keep only recent slow queries (prevent memory bloat)
                    if len(_slow_queries) > MAX_SLOW_QUERIES:
                        _slow_queries.pop(0)  # Remove oldest
                    
                    logger.warning(
                        f"🐌 Slow query detected: {query_name} "
                        f"({execution_time_ms:.2f}ms, threshold: {threshold_ms}ms)"
                        + (f", rows: {row_count}" if row_count else "")
                    )
                
                return result
                
            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Track error in patterns
                pattern = query_name.split('.')[-1]
                _query_patterns[pattern]['errors'] += 1
                
                metrics = QueryMetrics(
                    query_name=query_name,
                    execution_time_ms=execution_time_ms,
                    query_type=query_type,
                    error=str(e),
                )
                
                logger.error(
                    f"❌ Query error: {query_name} "
                    f"({execution_time_ms:.2f}ms) - {e}"
                )
                
                raise
        
        return wrapper
    return decorator


def get_query_stats() -> Dict[str, Dict[str, float]]:
    """
    Get query performance statistics
    
    Returns:
        Dictionary mapping query names to statistics (avg, min, max, count)
    """
    stats = {}
    
    for query_name, times in _query_stats.items():
        if times:
            stats[query_name] = {
                'count': len(times),
                'avg_ms': sum(times) / len(times),
                'min_ms': min(times),
                'max_ms': max(times),
                'total_ms': sum(times),
            }
    
    return stats


def get_slow_queries(
    limit: Optional[int] = None,
    min_time_ms: float = SLOW_QUERY_THRESHOLD_MS
) -> List[Dict[str, Any]]:
    """
    Get list of slow queries
    
    Args:
        limit: Maximum number of queries to return
        min_time_ms: Minimum execution time to include
    
    Returns:
        List of slow query dictionaries
    """
    filtered = [
        q for q in _slow_queries
        if q['time_ms'] >= min_time_ms
    ]
    
    # Sort by execution time (descending)
    filtered.sort(key=lambda x: x['time_ms'], reverse=True)
    
    if limit:
        return filtered[:limit]
    
    return filtered


def get_query_patterns() -> Dict[str, Dict[str, Any]]:
    """
    Get query pattern statistics (aggregated by function name)
    
    Returns:
        Dictionary mapping query patterns to statistics
    """
    patterns = {}
    
    for pattern, data in _query_patterns.items():
        if data['count'] > 0:
            patterns[pattern] = {
                'count': data['count'],
                'avg_time_ms': data['total_time_ms'] / data['count'],
                'min_time_ms': data['min_time_ms'] if data['min_time_ms'] != float('inf') else 0,
                'max_time_ms': data['max_time_ms'],
                'total_time_ms': data['total_time_ms'],
                'errors': data['errors'],
                'error_rate': data['errors'] / data['count'] if data['count'] > 0 else 0,
            }
    
    return patterns


def get_query_summary() -> Dict[str, Any]:
    """Get summary of all query statistics"""
    stats = get_query_stats()
    slow_queries = get_slow_queries()
    patterns = get_query_patterns()
    
    total_queries = sum(s['count'] for s in stats.values())
    total_time_ms = sum(s['total_ms'] for s in stats.values())
    
    # Aggregate patterns
    total_pattern_queries = sum(p['count'] for p in patterns.values())
    total_pattern_time = sum(p['total_time_ms'] for p in patterns.values())
    
    return {
        'total_queries': total_queries,
        'unique_queries': len(stats),
        'total_time_ms': total_time_ms,
        'avg_time_ms': total_time_ms / total_queries if total_queries > 0 else 0,
        'slow_queries_count': len(slow_queries),
        'top_slow_queries': slow_queries[:10],
        'query_stats': stats,
        'query_patterns': patterns,
        'pattern_summary': {
            'total_patterns': len(patterns),
            'total_queries': total_pattern_queries,
            'avg_time_ms': total_pattern_time / total_pattern_queries if total_pattern_queries > 0 else 0,
        },
    }


def clear_stats():
    """Clear all query statistics (useful for testing)"""
    global _query_stats, _slow_queries
    _query_stats.clear()
    _slow_queries.clear()
    logger.info("📊 Query statistics cleared")


def reset_slow_queries():
    """Clear slow queries list (but keep stats)"""
    global _slow_queries
    _slow_queries.clear()
    logger.info("📊 Slow queries list cleared")


# Context manager for manual query monitoring
class QueryTimer:
    """Context manager for timing queries manually"""
    
    def __init__(self, query_name: str, query_type: str = "unknown"):
        self.query_name = query_name
        self.query_type = query_type
        self.start_time = None
        self.execution_time_ms = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.execution_time_ms = (time.time() - self.start_time) * 1000
        
        # Track statistics
        _query_stats[self.query_name].append(self.execution_time_ms)
        
        # Check if slow query
        if self.execution_time_ms > SLOW_QUERY_THRESHOLD_MS:
            _slow_queries.append({
                'name': self.query_name,
                'time_ms': self.execution_time_ms,
                'timestamp': datetime.now().isoformat(),
                'type': self.query_type,
                'row_count': None,
            })
            
            logger.warning(
                f"🐌 Slow query: {self.query_name} "
                f"({self.execution_time_ms:.2f}ms)"
            )
        
        return False


# Example usage:
# 
# @monitor_query(threshold_ms=50, query_type='select')
# def get_posts(limit=100):
#     return db.query("SELECT * FROM posts LIMIT ?", (limit,))
#
# # Or with context manager:
# with QueryTimer("get_high_quality_posts", query_type='select'):
#     posts = db.query("SELECT * FROM posts WHERE value_score > 7")

