#!/usr/bin/env python3
"""
Load Test Script for Prismind
==============================

Tests API endpoints, database operations, and workers under expected load.
Identifies performance bottlenecks and validates system can handle production traffic.

Usage:
    python scripts/testing/load_test.py
    python scripts/testing/load_test.py --duration 300 --concurrent 50
"""

import argparse
import asyncio
import statistics
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

import httpx
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.infrastructure.monitoring.metrics import get_metrics_collector
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class LoadTestResults:
    """Store load test results"""

    def __init__(self):
        self.start_time = time.time()
        self.results: List[Dict] = []
        self.errors: List[Dict] = []

    def record_request(
        self, endpoint: str, method: str, duration: float, status_code: int, error: str = None
    ):
        """Record a request result"""
        result = {
            "endpoint": endpoint,
            "method": method,
            "duration": duration,
            "status_code": status_code,
            "timestamp": time.time(),
            "error": error,
        }

        if error or status_code >= 400:
            self.errors.append(result)
        else:
            self.results.append(result)

    def get_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.results:
            return {"error": "No successful requests"}

        durations = [r["duration"] for r in self.results]
        status_codes = defaultdict(int)
        for r in self.results + self.errors:
            status_codes[r["status_code"]] += 1

        total_requests = len(self.results) + len(self.errors)
        elapsed_time = time.time() - self.start_time

        return {
            "total_requests": total_requests,
            "successful_requests": len(self.results),
            "failed_requests": len(self.errors),
            "success_rate": (len(self.results) / total_requests * 100) if total_requests > 0 else 0,
            "requests_per_second": total_requests / elapsed_time if elapsed_time > 0 else 0,
            "duration_stats": {
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
                "min": min(durations),
                "max": max(durations),
                "p95": self._percentile(durations, 95),
                "p99": self._percentile(durations, 99),
            },
            "status_codes": dict(status_codes),
            "elapsed_time": elapsed_time,
            "error_count": len(self.errors),
        }

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


def test_endpoint(base_url: str, endpoint: str, method: str = "GET") -> Dict:
    """Test a single endpoint"""
    start_time = time.time()
    url = f"{base_url}{endpoint}"

    try:
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                response = client.get(url)
            elif method == "POST":
                response = client.post(url, json={})
            else:
                response = client.request(method, url)

            duration = time.time() - start_time

            return {
                "endpoint": endpoint,
                "method": method,
                "duration": duration,
                "status_code": response.status_code,
                "error": None,
            }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "endpoint": endpoint,
            "method": method,
            "duration": duration,
            "status_code": 0,
            "error": str(e),
        }


def load_test_api(base_url: str, duration: int, concurrent: int, endpoints: List[str]):
    """Run load test on API endpoints"""

    print(f"\n🚀 Starting API load test...")
    print(f"   Duration: {duration}s")
    print(f"   Concurrent: {concurrent}")
    print(f"   Endpoints: {', '.join(endpoints)}")

    results = LoadTestResults()
    stop_time = time.time() + duration

    def worker():
        """Worker function for load testing"""
        while time.time() < stop_time:
            for endpoint in endpoints:
                result = test_endpoint(base_url, endpoint)
                results.record_request(
                    result["endpoint"],
                    result["method"],
                    result["duration"],
                    result["status_code"],
                    result["error"],
                )

    # Run concurrent workers
    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = [executor.submit(worker) for _ in range(concurrent)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Worker error: {e}")

    return results


def test_database_operations(iterations: int = 100):
    """Test database operations under load"""

    print(f"\n🗄️  Starting database load test...")
    print(f"   Iterations: {iterations}")

    results = LoadTestResults()

    try:
        from src.services.new_database_manager import get_database_manager
        from src.infrastructure.monitoring.metrics import get_metrics_collector

        db = get_database_manager()
        metrics_collector = get_metrics_collector()

        for i in range(iterations):
            start_time = time.time()

            try:
                # Read operation
                posts = db.get_posts(limit=10)
                duration = time.time() - start_time

                results.record_request("db_get_posts", "GET", duration, 200)

            except Exception as e:
                duration = time.time() - start_time
                results.record_request("db_get_posts", "GET", duration, 500, str(e))

        # Get database metrics
        db_metrics = metrics_collector.get_database_performance(hours=1)

    except ImportError:
        print("⚠️  Database manager not available, skipping database test")
        return None

    return results, db_metrics


def test_worker_queues(base_url: str, jobs: int = 50):
    """Test worker queues under load"""

    print(f"\n⚙️  Starting worker queue load test...")
    print(f"   Jobs: {jobs}")

    results = LoadTestResults()

    try:
        with httpx.Client(timeout=60.0) as client:
            # Enqueue jobs
            for i in range(jobs):
                start_time = time.time()

                try:
                    response = client.post(
                        f"{base_url}/jobs/collect",
                        json={"platform": "threads", "force_once": False},
                    )
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        job_id = response.json().get("id")
                        results.record_request("/jobs/collect", "POST", duration, 200)

                        # Check job status
                        status_response = client.get(f"{base_url}/jobs/{job_id}")
                        results.record_request(
                            f"/jobs/{job_id}", "GET", duration, status_response.status_code
                        )
                    else:
                        results.record_request(
                            "/jobs/collect", "POST", duration, response.status_code
                        )

                except Exception as e:
                    duration = time.time() - start_time
                    results.record_request("/jobs/collect", "POST", duration, 0, str(e))

    except Exception as e:
        logger.error(f"Worker queue test error: {e}")

    return results


def print_summary(results: LoadTestResults, test_name: str):
    """Print test summary"""
    summary = results.get_summary()

    print(f"\n{'='*60}")
    print(f"{test_name} - Results")
    print(f"{'='*60}")
    print(f"Total Requests:      {summary['total_requests']}")
    print(f"Successful:          {summary['successful_requests']}")
    print(f"Failed:              {summary['failed_requests']}")
    print(f"Success Rate:        {summary['success_rate']:.2f}%")
    print(f"Requests/sec:        {summary['requests_per_second']:.2f}")
    print(f"\nDuration Statistics (seconds):")
    print(f"  Mean:              {summary['duration_stats']['mean']:.3f}")
    print(f"  Median:            {summary['duration_stats']['median']:.3f}")
    print(f"  P95:               {summary['duration_stats']['p95']:.3f}")
    print(f"  P99:               {summary['duration_stats']['p99']:.3f}")
    print(f"  Min:               {summary['duration_stats']['min']:.3f}")
    print(f"  Max:               {summary['duration_stats']['max']:.3f}")

    if summary.get("status_codes"):
        print(f"\nStatus Codes:")
        for code, count in summary["status_codes"].items():
            print(f"  {code}: {count}")

    if results.errors:
        print(f"\n⚠️  Errors ({len(results.errors)}):")
        for error in results.errors[:5]:  # Show first 5 errors
            print(f"  {error['endpoint']}: {error.get('error', error['status_code'])}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Load test Prismind services")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base API URL")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--endpoints", nargs="+", default=["/health", "/health/ready"], help="Endpoints to test")
    parser.add_argument("--db-iterations", type=int, default=100, help="Database test iterations")
    parser.add_argument("--jobs", type=int, default=20, help="Number of jobs for queue test")

    args = parser.parse_args()

    print("=" * 60)
    print("Prismind Load Test")
    print("=" * 60)
    print(f"Base URL: {args.base_url}")
    print(f"Duration: {args.duration}s")
    print(f"Concurrent: {args.concurrent}")

    # System resource check
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    print(f"\nSystem Resources:")
    print(f"  CPU: {cpu_percent}%")
    print(f"  Memory: {memory.percent}%")

    # Test 1: API Load Test
    api_results = load_test_api(args.base_url, args.duration, args.concurrent, args.endpoints)
    print_summary(api_results, "API Load Test")

    # Test 2: Database Operations
    db_results = test_database_operations(args.db_iterations)
    if db_results:
        results, metrics = db_results
        print_summary(results, "Database Load Test")

    # Test 3: Worker Queues
    queue_results = test_worker_queues(args.base_url, args.jobs)
    print_summary(queue_results, "Worker Queue Load Test")

    # Final summary
    print(f"\n{'='*60}")
    print("Load Test Complete")
    print(f"{'='*60}")

    # Check for bottlenecks
    api_summary = api_results.get_summary()
    if api_summary["duration_stats"]["p95"] > 1.0:
        print("⚠️  WARNING: P95 response time > 1s, consider optimization")
    if api_summary["success_rate"] < 95:
        print("⚠️  WARNING: Success rate < 95%, investigate failures")

    return 0


if __name__ == "__main__":
    exit(main())






