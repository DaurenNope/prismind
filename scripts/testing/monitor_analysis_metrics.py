#!/usr/bin/env python3
"""
Monitor Analysis Pipeline Metrics
==================================

Monitors production metrics for the analysis pipeline:
- orchestrator.analyze_batch.post_success
- Cache hit rates
- Rate limiting issues
- Performance trends

Usage:
    python scripts/testing/monitor_analysis_metrics.py
    python scripts/testing/monitor_analysis_metrics.py --watch
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.domain.analysis.analyzers.intelligent_content_analyzer import _analysis_cache
from src.infrastructure.monitoring.metrics import get_metrics_collector
from src.infrastructure.monitoring.performance_monitor import get_performance_monitor
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricsMonitor:
    """Monitor analysis pipeline metrics"""

    def __init__(self):
        self.metrics_collector = get_metrics_collector()
        self.perf_monitor = get_performance_monitor()

    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        cache_size = len(_analysis_cache.cache)
        
        # Count expired entries
        now = datetime.now()
        expired = 0
        valid = 0
        for cached_time, _ in _analysis_cache.cache.values():
            age = now - cached_time
            if age < _analysis_cache.ttl:
                valid += 1
            else:
                expired += 1

        return {
            "total_entries": cache_size,
            "valid_entries": valid,
            "expired_entries": expired,
            "cache_size_mb": cache_size * 0.001,  # Rough estimate
        }

    def get_analysis_metrics(self, hours: int = 1) -> dict:
        """Get analysis metrics from last N hours"""
        summary = self.metrics_collector.get_metrics_summary(hours=hours)
        
        # Extract analysis-specific metrics
        analysis_ops = summary.get("database_metrics", {}).get("db_analyze_post", {})
        
        return {
            "operation_count": analysis_ops.get("count", 0),
            "avg_duration_ms": analysis_ops.get("avg_ms", 0),
            "error_rate": analysis_ops.get("error_rate", 0),
        }

    def check_rate_limiting(self) -> list:
        """Check for rate limiting issues"""
        issues = []
        
        # Check for high error rates
        metrics = self.get_analysis_metrics(hours=1)
        if metrics.get("error_rate", 0) > 10:
            issues.append(f"High error rate: {metrics['error_rate']:.1f}%")

        # Check for slow operations
        if metrics.get("avg_duration_ms", 0) > 3000:
            issues.append(f"Slow operations: {metrics['avg_duration_ms']:.0f}ms average")

        # Check system resources
        dashboard = self.perf_monitor.get_dashboard_data()
        system_status = dashboard.get("system_status", "unknown")
        
        if system_status == "critical":
            issues.append("System status: CRITICAL")
        elif system_status == "degraded":
            issues.append("System status: DEGRADED")

        return issues

    def print_metrics_report(self, hours: int = 1):
        """Print comprehensive metrics report"""
        print(f"\n{'='*60}")
        print(f"Analysis Pipeline Metrics Report")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Period: Last {hours} hour(s)")
        print(f"{'='*60}")

        # Cache Statistics
        cache_stats = self.get_cache_stats()
        print(f"\n📦 Cache Statistics:")
        print(f"   Total entries: {cache_stats['total_entries']}")
        print(f"   Valid entries: {cache_stats['valid_entries']}")
        print(f"   Expired entries: {cache_stats['expired_entries']}")
        print(f"   Estimated size: {cache_stats['cache_size_mb']:.2f} MB")

        # Analysis Metrics
        analysis_metrics = self.get_analysis_metrics(hours=hours)
        print(f"\n📊 Analysis Metrics (last {hours}h):")
        print(f"   Operations: {analysis_metrics['operation_count']}")
        print(f"   Avg duration: {analysis_metrics['avg_duration_ms']:.0f}ms")
        print(f"   Error rate: {analysis_metrics['error_rate']:.1f}%")

        if analysis_metrics['operation_count'] > 0:
            time_per_post = analysis_metrics['avg_duration_ms'] / 1000
            print(f"   Time per post: {time_per_post:.3f}s")
            
            if time_per_post < 3.0:
                print(f"   Status: ✅ Within target (<3s)")
            else:
                print(f"   Status: ⚠️  Above target (<3s)")

        # Performance Monitor Data
        dashboard = self.perf_monitor.get_dashboard_data()
        print(f"\n🔍 System Status:")
        print(f"   Status: {dashboard.get('system_status', 'unknown').upper()}")
        
        api_perf = dashboard.get("api_performance", {})
        if api_perf:
            print(f"\n   API Performance:")
            for endpoint, stats in list(api_perf.items())[:5]:  # Top 5 endpoints
                print(f"      {endpoint}:")
                print(f"         Avg response: {stats.get('avg_response_time', 0):.3f}s")
                print(f"         Error rate: {stats.get('error_rate', 0):.1f}%")

        # Rate Limiting Check
        issues = self.check_rate_limiting()
        if issues:
            print(f"\n⚠️  Potential Issues:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print(f"\n✅ No issues detected")

        # Recommendations
        print(f"\n💡 Recommendations:")
        
        cache_hit_estimate = cache_stats['valid_entries'] / max(cache_stats['total_entries'], 1) * 100
        if cache_hit_estimate < 30:
            print(f"   • Low cache utilization - consider increasing TTL")
        elif cache_hit_estimate > 70:
            print(f"   • High cache effectiveness - cache is working well")

        if analysis_metrics['error_rate'] > 5:
            print(f"   • High error rate - investigate failures")
        
        if analysis_metrics['avg_duration_ms'] > 3000:
            print(f"   • Slow operations - consider tuning concurrent limit")

        print()

    def watch_mode(self, interval: int = 60):
        """Continuous monitoring mode"""
        print(f"\n👀 Monitoring mode - updating every {interval}s")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                self.print_metrics_report(hours=1)
                print(f"Next update in {interval}s...\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n⚠️  Monitoring stopped")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Monitor analysis pipeline metrics")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=60, help="Update interval in seconds (default: 60)")
    parser.add_argument("--hours", type=int, default=1, help="Metrics period in hours (default: 1)")

    args = parser.parse_args()

    monitor = MetricsMonitor()

    if args.watch:
        monitor.watch_mode(interval=args.interval)
    else:
        monitor.print_metrics_report(hours=args.hours)

    return 0


if __name__ == "__main__":
    exit(main())

