#!/usr/bin/env python3
"""
Database Performance Monitor
============================
Monitors query performance improvements after migrations
Created: 2025-11-20
Priority: P1 - Performance monitoring

Usage:
    python scripts/database/monitor_performance.py [--baseline] [--compare] [--report]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.query_monitor import get_query_summary, get_slow_queries
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)

PERFORMANCE_LOG = Path(project_root) / "data" / "analytics" / "query_performance.jsonl"
PERFORMANCE_LOG.parent.mkdir(parents=True, exist_ok=True)


def save_baseline() -> Dict[str, any]:
    """
    Save current performance metrics as baseline
    
    Returns:
        Baseline metrics dictionary
    """
    logger.info("📊 Saving performance baseline...")
    
    summary = get_query_summary()
    
    baseline = {
        'timestamp': datetime.now().isoformat(),
        'type': 'baseline',
        'total_queries': summary['total_queries'],
        'unique_queries': summary['unique_queries'],
        'avg_time_ms': summary['avg_time_ms'],
        'slow_queries_count': summary['slow_queries_count'],
        'query_stats': summary['query_stats'],
        'pattern_summary': summary.get('pattern_summary', {}),
    }
    
    # Save to log file
    with open(PERFORMANCE_LOG, 'a') as f:
        f.write(json.dumps(baseline) + '\n')
    
    logger.info(f"✅ Baseline saved: {baseline['timestamp']}")
    logger.info(f"   Total queries: {baseline['total_queries']}")
    logger.info(f"   Avg time: {baseline['avg_time_ms']:.2f}ms")
    logger.info(f"   Slow queries: {baseline['slow_queries_count']}")
    
    return baseline


def save_performance_snapshot() -> Dict[str, any]:
    """
    Save current performance snapshot
    
    Returns:
        Performance snapshot dictionary
    """
    summary = get_query_summary()
    
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'type': 'snapshot',
        'total_queries': summary['total_queries'],
        'unique_queries': summary['unique_queries'],
        'avg_time_ms': summary['avg_time_ms'],
        'slow_queries_count': summary['slow_queries_count'],
        'query_stats': summary['query_stats'],
        'pattern_summary': summary.get('pattern_summary', {}),
        'top_slow_queries': summary.get('top_slow_queries', [])[:10],
    }
    
    # Save to log file
    with open(PERFORMANCE_LOG, 'a') as f:
        f.write(json.dumps(snapshot) + '\n')
    
    return snapshot


def load_baseline() -> Optional[Dict[str, any]]:
    """
    Load most recent baseline from log
    
    Returns:
        Baseline dictionary or None
    """
    if not PERFORMANCE_LOG.exists():
        return None
    
    try:
        with open(PERFORMANCE_LOG, 'r') as f:
            for line in reversed(list(f)):
                data = json.loads(line.strip())
                if data.get('type') == 'baseline':
                    return data
    except Exception as e:
        logger.error(f"❌ Error loading baseline: {e}")
    
    return None


def compare_with_baseline(baseline: Dict[str, any], current: Dict[str, any]) -> Dict[str, any]:
    """
    Compare current performance with baseline
    
    Returns:
        Comparison dictionary with improvements/regressions
    """
    comparison = {
        'baseline_timestamp': baseline['timestamp'],
        'current_timestamp': current['timestamp'],
        'improvements': [],
        'regressions': [],
        'unchanged': [],
    }
    
    # Compare average time
    baseline_avg = baseline.get('avg_time_ms', 0)
    current_avg = current.get('avg_time_ms', 0)
    
    if baseline_avg > 0:
        avg_change_pct = ((current_avg - baseline_avg) / baseline_avg) * 100
        
        if avg_change_pct < -5:  # 5% improvement
            comparison['improvements'].append({
                'metric': 'avg_query_time',
                'baseline': baseline_avg,
                'current': current_avg,
                'improvement_pct': abs(avg_change_pct),
            })
        elif avg_change_pct > 5:  # 5% regression
            comparison['regressions'].append({
                'metric': 'avg_query_time',
                'baseline': baseline_avg,
                'current': current_avg,
                'regression_pct': avg_change_pct,
            })
        else:
            comparison['unchanged'].append({
                'metric': 'avg_query_time',
                'baseline': baseline_avg,
                'current': current_avg,
            })
    
    # Compare slow query count
    baseline_slow = baseline.get('slow_queries_count', 0)
    current_slow = current.get('slow_queries_count', 0)
    
    if baseline_slow > 0:
        slow_change_pct = ((current_slow - baseline_slow) / baseline_slow) * 100
        
        if slow_change_pct < -10:  # 10% reduction in slow queries
            comparison['improvements'].append({
                'metric': 'slow_queries_count',
                'baseline': baseline_slow,
                'current': current_slow,
                'improvement_pct': abs(slow_change_pct),
            })
        elif slow_change_pct > 10:
            comparison['regressions'].append({
                'metric': 'slow_queries_count',
                'baseline': baseline_slow,
                'current': current_slow,
                'regression_pct': slow_change_pct,
            })
    
    return comparison


def print_performance_report(comparison: Dict[str, any]):
    """Print performance comparison report"""
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE COMPARISON REPORT")
    print("=" * 80)
    
    print(f"\n📅 Baseline: {comparison['baseline_timestamp']}")
    print(f"📅 Current:  {comparison['current_timestamp']}")
    
    if comparison['improvements']:
        print(f"\n✅ IMPROVEMENTS ({len(comparison['improvements'])}):")
        for imp in comparison['improvements']:
            print(f"   • {imp['metric']}:")
            print(f"     Baseline: {imp['baseline']:.2f}")
            print(f"     Current:  {imp['current']:.2f}")
            print(f"     Improvement: {imp['improvement_pct']:.1f}%")
    
    if comparison['regressions']:
        print(f"\n⚠️  REGRESSIONS ({len(comparison['regressions'])}):")
        for reg in comparison['regressions']:
            print(f"   • {reg['metric']}:")
            print(f"     Baseline: {reg['baseline']:.2f}")
            print(f"     Current:  {reg['current']:.2f}")
            print(f"     Regression: {reg['regression_pct']:.1f}%")
    
    if comparison['unchanged']:
        print(f"\n➡️  UNCHANGED ({len(comparison['unchanged'])}):")
        for unchanged in comparison['unchanged']:
            print(f"   • {unchanged['metric']}")
    
    print("\n" + "=" * 80)


def generate_report() -> Dict[str, any]:
    """Generate comprehensive performance report"""
    logger.info("📊 Generating performance report...")
    
    # Load all snapshots
    snapshots = []
    if PERFORMANCE_LOG.exists():
        with open(PERFORMANCE_LOG, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    snapshots.append(data)
                except:
                    continue
    
    if not snapshots:
        logger.warning("⚠️  No performance data found")
        return {}
    
    # Get baseline
    baseline = next((s for s in snapshots if s.get('type') == 'baseline'), None)
    if not baseline:
        logger.warning("⚠️  No baseline found")
        baseline = snapshots[0]  # Use first snapshot as baseline
    
    # Get latest snapshot
    latest = snapshots[-1]
    
    # Compare
    comparison = compare_with_baseline(baseline, latest)
    
    # Print report
    print_performance_report(comparison)
    
    return comparison


def main():
    parser = argparse.ArgumentParser(description="Monitor database query performance")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Save current metrics as baseline"
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Save current performance snapshot"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare current performance with baseline"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate comprehensive performance report"
    )
    
    args = parser.parse_args()
    
    if args.baseline:
        save_baseline()
    
    elif args.snapshot:
        snapshot = save_performance_snapshot()
        logger.info(f"✅ Snapshot saved: {snapshot['timestamp']}")
    
    elif args.compare:
        baseline = load_baseline()
        if not baseline:
            logger.error("❌ No baseline found. Run with --baseline first")
            sys.exit(1)
        
        current = save_performance_snapshot()
        comparison = compare_with_baseline(baseline, current)
        print_performance_report(comparison)
    
    elif args.report:
        generate_report()
    
    else:
        # Default: show current stats
        summary = get_query_summary()
        
        print("\n" + "=" * 80)
        print("📊 CURRENT PERFORMANCE STATS")
        print("=" * 80)
        
        print(f"\nTotal Queries: {summary['total_queries']}")
        print(f"Unique Queries: {summary['unique_queries']}")
        print(f"Average Time: {summary['avg_time_ms']:.2f}ms")
        print(f"Slow Queries: {summary['slow_queries_count']}")
        
        if summary.get('top_slow_queries'):
            print(f"\n🐌 Top Slow Queries:")
            for query in summary['top_slow_queries'][:5]:
                print(f"   • {query['name']}: {query['time_ms']:.2f}ms")
        
        print()


if __name__ == "__main__":
    main()






