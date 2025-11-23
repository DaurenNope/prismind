#!/usr/bin/env python3
"""
Performance Benchmark Script for Analysis Pipeline
===================================================

Tests the performance optimizations:
- Batch duplicate checks
- Parallel processing
- Caching layer

Usage:
    python scripts/testing/benchmark_analysis_performance.py
    python scripts/testing/benchmark_analysis_performance.py --posts 100 --concurrent 5
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import statistics
import time
from datetime import datetime

from src.domain.analysis.analyzers.intelligent_content_analyzer import _analysis_cache
from src.infrastructure.monitoring.metrics import get_metrics_collector
from src.application.automation.orchestrator import Orchestrator
from src.infrastructure.database.storage.db import get_storage
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class PerformanceBenchmark:
    """Benchmark analysis pipeline performance"""

    def __init__(self):
        self.orchestrator = Orchestrator()
        self.storage = get_storage()
        self.metrics_collector = get_metrics_collector()
        self.results = {
            "batch_duplicate_check": {},
            "parallel_processing": {},
            "caching": {},
            "overall": {},
        }

    async def benchmark_batch_duplicate_checks(self, num_posts: int = 100):
        """Benchmark batch duplicate check performance"""
        print(f"\n{'='*60}")
        print("📊 Benchmark 1: Batch Duplicate Checks")
        print(f"{'='*60}")

        # Generate test posts
        test_posts = []
        for i in range(num_posts):
            test_posts.append({
                "post_id": f"test_post_{i}",
                "url": f"https://example.com/post/{i}",
                "platform": "twitter",
                "content": f"Test post content {i}",
            })

        # Time batch check
        start_time = time.time()
        duplicates = self.storage.check_batch_duplicates(test_posts)
        batch_time = time.time() - start_time

        print(f"   Posts checked: {num_posts}")
        print(f"   Batch check time: {batch_time:.3f}s")
        print(f"   Time per post: {(batch_time / num_posts) * 1000:.2f}ms")
        print(f"   Duplicates found: {sum(1 for v in duplicates.values() if v)}")

        self.results["batch_duplicate_check"] = {
            "total_posts": num_posts,
            "batch_time": batch_time,
            "time_per_post_ms": (batch_time / num_posts) * 1000,
            "duplicates_found": sum(1 for v in duplicates.values() if v),
        }

        return duplicates

    async def benchmark_parallel_processing(
        self, num_posts: int = 50, concurrent: int = 5
    ):
        """Benchmark parallel processing performance"""
        print(f"\n{'='*60}")
        print("📊 Benchmark 2: Parallel Processing")
        print(f"{'='*60}")
        print(f"   Posts to analyze: {num_posts}")
        print(f"   Concurrent limit: {concurrent}")

        # Clear cache to test fresh analysis
        _analysis_cache.clear()
        cache_size_before = len(_analysis_cache.cache)

        # Get unanalyzed posts
        posts = self.storage.get_unanalyzed_posts(limit=num_posts)
        
        if not posts:
            print("   ⚠️  No unanalyzed posts available for benchmarking")
            print("   Using first available posts instead...")
            posts = self.storage.get_posts(limit=num_posts)

        if not posts:
            print("   ❌ No posts available for benchmarking")
            return

        actual_num = len(posts)
        print(f"   Actual posts found: {actual_num}")

        # Time parallel analysis
        start_time = time.time()
        
        try:
            result = await self.orchestrator.analyze_batch(limit=actual_num, force=False)
            
            if isinstance(result, dict):
                count = result.get("count", 0)
            else:
                count = result if isinstance(result, int) else 0
                
            total_time = time.time() - start_time
            
            cache_size_after = len(_analysis_cache.cache)

        except Exception as e:
            logger.error(f"Benchmark error: {e}")
            total_time = time.time() - start_time
            count = 0
            cache_size_after = len(_analysis_cache.cache)

        time_per_post = total_time / actual_num if actual_num > 0 else 0
        posts_per_second = actual_num / total_time if total_time > 0 else 0

        print(f"   Total time: {total_time:.2f}s")
        print(f"   Posts analyzed: {count}")
        print(f"   Time per post: {time_per_post:.3f}s")
        print(f"   Posts per second: {posts_per_second:.2f}")
        print(f"   Cache entries created: {cache_size_after - cache_size_before}")

        self.results["parallel_processing"] = {
            "total_posts": actual_num,
            "posts_analyzed": count,
            "total_time": total_time,
            "time_per_post": time_per_post,
            "posts_per_second": posts_per_second,
            "cache_entries": cache_size_after - cache_size_before,
        }

        return count, time_per_post

    async def benchmark_caching(self, num_posts: int = 20):
        """Benchmark cache effectiveness"""
        print(f"\n{'='*60}")
        print("📊 Benchmark 3: Caching Layer")
        print(f"{'='*60}")

        # Clear cache
        _analysis_cache.clear()
        
        # Get posts to analyze
        posts = self.storage.get_unanalyzed_posts(limit=num_posts)
        if not posts:
            posts = self.storage.get_posts(limit=num_posts)
        
        if not posts:
            print("   ❌ No posts available for caching benchmark")
            return

        actual_num = min(len(posts), num_posts)
        print(f"   Posts to test: {actual_num}")

        # First pass: Analyze without cache (warm cache)
        print("\n   First pass (warm cache)...")
        start_time = time.time()
        try:
            result1 = await self.orchestrator.analyze_batch(limit=actual_num, force=True)
            first_pass_time = time.time() - start_time
            if isinstance(result1, dict):
                count1 = result1.get("count", 0)
            else:
                count1 = result1 if isinstance(result1, int) else 0
        except Exception as e:
            logger.error(f"First pass error: {e}")
            first_pass_time = time.time() - start_time
            count1 = 0

        cache_size_after_first = len(_analysis_cache.cache)
        print(f"   Time: {first_pass_time:.2f}s")
        print(f"   Cache entries: {cache_size_after_first}")

        # Second pass: Analyze with cache (should be faster)
        print("\n   Second pass (with cache)...")
        start_time = time.time()
        try:
            result2 = await self.orchestrator.analyze_batch(limit=actual_num, force=True)
            second_pass_time = time.time() - start_time
            if isinstance(result2, dict):
                count2 = result2.get("count", 0)
            else:
                count2 = result2 if isinstance(result2, int) else 0
        except Exception as e:
            logger.error(f"Second pass error: {e}")
            second_pass_time = time.time() - start_time
            count2 = 0

        cache_size_after_second = len(_analysis_cache.cache)

        if first_pass_time > 0:
            speedup = first_pass_time / second_pass_time if second_pass_time > 0 else 0
            cache_hit_rate = (cache_size_after_first / actual_num * 100) if actual_num > 0 else 0
        else:
            speedup = 0
            cache_hit_rate = 0

        print(f"   Time: {second_pass_time:.2f}s")
        print(f"   Speedup: {speedup:.2f}x")
        print(f"   Cache hit rate: {cache_hit_rate:.1f}%")
        print(f"   Cache entries: {cache_size_after_second}")

        self.results["caching"] = {
            "first_pass_time": first_pass_time,
            "second_pass_time": second_pass_time,
            "speedup": speedup,
            "cache_hit_rate": cache_hit_rate,
            "cache_entries": cache_size_after_second,
        }

    async def benchmark_overall(self, num_posts: int = 100):
        """Run overall performance benchmark"""
        print(f"\n{'='*60}")
        print("📊 Overall Performance Benchmark")
        print(f"{'='*60}")
        print(f"   Batch size: {num_posts} posts")

        # Clear cache
        _analysis_cache.clear()

        # Get posts
        posts = self.storage.get_unanalyzed_posts(limit=num_posts)
        if not posts:
            posts = self.storage.get_posts(limit=num_posts)

        if not posts:
            print("   ❌ No posts available")
            return

        actual_num = len(posts)
        print(f"   Actual posts: {actual_num}")

        # Benchmark overall pipeline
        start_time = time.time()

        try:
            # Batch duplicate check
            dup_start = time.time()
            duplicates = self.storage.check_batch_duplicates(posts[:50])  # Check first 50
            dup_time = time.time() - dup_start

            # Parallel analysis
            result = await self.orchestrator.analyze_batch(limit=actual_num, force=False)
            
            total_time = time.time() - start_time
            
            if isinstance(result, dict):
                analyzed_count = result.get("count", 0)
            else:
                analyzed_count = result if isinstance(result, int) else 0

        except Exception as e:
            logger.error(f"Overall benchmark error: {e}")
            total_time = time.time() - start_time
            analyzed_count = 0
            dup_time = 0

        time_per_post = total_time / actual_num if actual_num > 0 else 0
        cache_size = len(_analysis_cache.cache)

        print(f"\n   Results:")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Posts analyzed: {analyzed_count}")
        print(f"   Time per post: {time_per_post:.3f}s")
        print(f"   Duplicate check time: {dup_time:.3f}s")
        print(f"   Cache entries: {cache_size}")

        self.results["overall"] = {
            "total_posts": actual_num,
            "posts_analyzed": analyzed_count,
            "total_time": total_time,
            "time_per_post": time_per_post,
            "duplicate_check_time": dup_time,
            "cache_entries": cache_size,
        }

        # Performance evaluation
        print(f"\n   Performance Evaluation:")
        if time_per_post < 3.0:
            print(f"   ✅ EXCELLENT: {time_per_post:.3f}s/post (target: <3s)")
        elif time_per_post < 5.0:
            print(f"   ✅ GOOD: {time_per_post:.3f}s/post (target: <3s)")
        elif time_per_post < 10.0:
            print(f"   ⚠️  ACCEPTABLE: {time_per_post:.3f}s/post (target: <3s)")
        else:
            print(f"   ❌ NEEDS IMPROVEMENT: {time_per_post:.3f}s/post (target: <3s)")

    def print_summary(self):
        """Print benchmark summary"""
        print(f"\n{'='*60}")
        print("📊 Benchmark Summary")
        print(f"{'='*60}")

        if self.results.get("batch_duplicate_check"):
            r = self.results["batch_duplicate_check"]
            print(f"\n1. Batch Duplicate Checks:")
            print(f"   Time per post: {r.get('time_per_post_ms', 0):.2f}ms")
            print(f"   Efficiency: ✅ Single query for {r.get('total_posts', 0)} posts")

        if self.results.get("parallel_processing"):
            r = self.results["parallel_processing"]
            print(f"\n2. Parallel Processing:")
            print(f"   Time per post: {r.get('time_per_post', 0):.3f}s")
            print(f"   Posts per second: {r.get('posts_per_second', 0):.2f}")
            print(f"   Cache entries: {r.get('cache_entries', 0)}")

        if self.results.get("caching"):
            r = self.results["caching"]
            print(f"\n3. Caching Layer:")
            print(f"   First pass: {r.get('first_pass_time', 0):.2f}s")
            print(f"   Second pass: {r.get('second_pass_time', 0):.2f}s")
            print(f"   Speedup: {r.get('speedup', 0):.2f}x")
            print(f"   Cache hit rate: {r.get('cache_hit_rate', 0):.1f}%")

        if self.results.get("overall"):
            r = self.results["overall"]
            print(f"\n4. Overall Performance:")
            print(f"   Time per post: {r.get('time_per_post', 0):.3f}s")
            print(f"   Target: <3.0s/post")
            if r.get("time_per_post", 0) < 3.0:
                print(f"   Status: ✅ TARGET MET")
            else:
                print(f"   Status: ⚠️  Above target (consider tuning)")

        # Recommendations
        print(f"\n{'='*60}")
        print("💡 Recommendations")
        print(f"{'='*60}")

        if self.results.get("parallel_processing"):
            r = self.results["parallel_processing"]
            time_per_post = r.get("time_per_post", 0)
            
            if time_per_post > 10.0:
                print("   • Increase concurrent limit (try 10 instead of 5)")
            elif time_per_post < 2.0:
                print("   • Current concurrency (5) is working well")
            else:
                print("   • Consider testing with concurrent=10 for better throughput")

        if self.results.get("caching"):
            r = self.results["caching"]
            hit_rate = r.get("cache_hit_rate", 0)
            
            if hit_rate < 50:
                print("   • Low cache hit rate - content may be too diverse")
                print("   • Consider increasing cache TTL to 2 hours")
            elif hit_rate > 80:
                print("   • High cache hit rate - caching is very effective")

        print()


async def main():
    """Main benchmark function"""
    parser = argparse.ArgumentParser(description="Benchmark analysis pipeline performance")
    parser.add_argument("--posts", type=int, default=50, help="Number of posts to test (default: 50)")
    parser.add_argument("--concurrent", type=int, default=5, help="Concurrent limit (default: 5)")
    parser.add_argument("--skip-cache", action="store_true", help="Skip cache benchmark")
    parser.add_argument("--overall-only", action="store_true", help="Run overall benchmark only")

    args = parser.parse_args()

    print("=" * 60)
    print("Performance Benchmark: Analysis Pipeline")
    print("=" * 60)
    print(f"Posts: {args.posts}")
    print(f"Concurrent: {args.concurrent}")

    benchmark = PerformanceBenchmark()

    try:
        if not args.overall_only:
            # Benchmark 1: Batch duplicate checks
            await benchmark.benchmark_batch_duplicate_checks(num_posts=min(args.posts, 100))

            # Benchmark 2: Parallel processing
            await benchmark.benchmark_parallel_processing(
                num_posts=args.posts, concurrent=args.concurrent
            )

            # Benchmark 3: Caching (if not skipped)
            if not args.skip_cache:
                await benchmark.benchmark_caching(num_posts=min(args.posts, 20))

        # Overall benchmark
        await benchmark.benchmark_overall(num_posts=args.posts)

    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user")
    except Exception as e:
        logger.exception(f"Benchmark error: {e}")
        print(f"\n❌ Benchmark failed: {e}")
        return 1
    finally:
        benchmark.print_summary()

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))

