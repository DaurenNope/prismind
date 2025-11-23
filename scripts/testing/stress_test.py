#!/usr/bin/env python3
"""
Stress Test Script for Prismind
=================================

Tests system under extreme load and failure scenarios.
Identifies breaking points and system behavior under stress.

Usage:
    python scripts/testing/stress_test.py
    python scripts/testing/stress_test.py --max-concurrent 200 --duration 600
"""

import argparse
import asyncio
import random
import signal
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import psutil

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class StressTest:
    """Stress test runner"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = defaultdict(list)
        self.errors = []
        self.start_time = time.time()
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        print("\n⚠️  Interrupt received, stopping stress test...")
        self.running = False

    def test_endpoint(self, endpoint: str, method: str = "GET", payload: dict = None):
        """Test endpoint under stress"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            with httpx.Client(timeout=60.0) as client:
                if method == "GET":
                    response = client.get(url)
                elif method == "POST":
                    response = client.post(url, json=payload or {})
                else:
                    response = client.request(method, url, json=payload)

                duration = time.time() - start_time

                self.results[endpoint].append({
                    "duration": duration,
                    "status_code": response.status_code,
                    "success": 200 <= response.status_code < 400,
                })

                if response.status_code >= 400:
                    self.errors.append({
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "duration": duration,
                    })

        except Exception as e:
            duration = time.time() - start_time
            self.errors.append({
                "endpoint": endpoint,
                "error": str(e),
                "duration": duration,
            })

    def ramp_up_test(self, endpoint: str, max_concurrent: int, ramp_duration: int):
        """Gradually increase load until failure"""
        print(f"\n📈 Ramp-up test: {endpoint}")
        print(f"   Max concurrent: {max_concurrent}")
        print(f"   Ramp duration: {ramp_duration}s")

        concurrent = 1
        increment = max(1, max_concurrent // 20)
        interval = ramp_duration / 20

        while concurrent <= max_concurrent and self.running:
            print(f"   Testing with {concurrent} concurrent requests...")

            with ThreadPoolExecutor(max_workers=concurrent) as executor:
                futures = [
                    executor.submit(self.test_endpoint, endpoint)
                    for _ in range(concurrent * 10)  # 10 requests per worker
                ]

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Request error: {e}")

            # Calculate success rate
            if self.results[endpoint]:
                recent = self.results[endpoint][-concurrent * 10:]
                success_rate = sum(1 for r in recent if r["success"]) / len(recent) * 100

                if success_rate < 50:
                    print(f"   ⚠️  Success rate dropped to {success_rate:.1f}%")
                    print(f"   💥 Breaking point reached at {concurrent} concurrent requests")
                    break

            concurrent += increment
            time.sleep(interval)

    def sustained_load_test(self, endpoints: list, concurrent: int, duration: int):
        """Sustained high load test"""
        print(f"\n🔥 Sustained load test")
        print(f"   Concurrent: {concurrent}")
        print(f"   Duration: {duration}s")

        stop_time = time.time() + duration

        def worker():
            """Worker for sustained load"""
            while time.time() < stop_time and self.running:
                endpoint = random.choice(endpoints)
                self.test_endpoint(endpoint)

        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [executor.submit(worker) for _ in range(concurrent)]

            # Monitor progress
            while time.time() < stop_time and self.running:
                time.sleep(5)
                elapsed = time.time() - self.start_time
                total_requests = sum(len(results) for results in self.results.values())
                print(f"   Progress: {elapsed:.0f}s / {duration}s | Requests: {total_requests}")

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Worker error: {e}")

    def burst_test(self, endpoint: str, burst_size: int):
        """Burst traffic test"""
        print(f"\n💥 Burst test: {endpoint}")
        print(f"   Burst size: {burst_size} requests")

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=burst_size) as executor:
            futures = [executor.submit(self.test_endpoint, endpoint) for _ in range(burst_size)]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Burst request error: {e}")

        elapsed = time.time() - start_time
        print(f"   Burst completed in {elapsed:.2f}s")
        print(f"   Rate: {burst_size / elapsed:.2f} req/s")

    def resource_exhaustion_test(self, endpoint: str):
        """Test resource exhaustion scenarios"""
        print(f"\n⛔ Resource exhaustion test: {endpoint}")

        # Monitor system resources
        initial_cpu = psutil.cpu_percent(interval=1)
        initial_memory = psutil.virtual_memory().percent

        print(f"   Initial CPU: {initial_cpu}%")
        print(f"   Initial Memory: {initial_memory}%")

        # Create sustained high load
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = []
            for i in range(1000):
                futures.append(executor.submit(self.test_endpoint, endpoint))
                if i % 100 == 0:
                    cpu = psutil.cpu_percent(interval=0.1)
                    memory = psutil.virtual_memory().percent
                    print(f"   Request {i}: CPU {cpu}%, Memory {memory}%")

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Resource test error: {e}")

        final_cpu = psutil.cpu_percent(interval=1)
        final_memory = psutil.virtual_memory().percent

        print(f"   Final CPU: {final_cpu}%")
        print(f"   Final Memory: {final_memory}%")
        print(f"   CPU increase: {final_cpu - initial_cpu:.1f}%")
        print(f"   Memory increase: {final_memory - initial_memory:.1f}%")

    def print_summary(self):
        """Print test summary"""
        elapsed = time.time() - self.start_time
        total_requests = sum(len(results) for results in self.results.values())
        total_errors = len(self.errors)

        print(f"\n{'='*60}")
        print("Stress Test Summary")
        print(f"{'='*60}")
        print(f"Duration:           {elapsed:.1f}s")
        print(f"Total Requests:     {total_requests}")
        print(f"Total Errors:       {total_errors}")
        print(f"Error Rate:         {total_errors / total_requests * 100:.2f}%" if total_requests > 0 else "N/A")

        print(f"\nResults by Endpoint:")
        for endpoint, results in self.results.items():
            if results:
                durations = [r["duration"] for r in results]
                successes = sum(1 for r in results if r["success"])
                avg_duration = sum(durations) / len(durations)
                success_rate = successes / len(results) * 100

                print(f"  {endpoint}:")
                print(f"    Requests:     {len(results)}")
                print(f"    Success Rate: {success_rate:.1f}%")
                print(f"    Avg Duration: {avg_duration:.3f}s")
                print(f"    Max Duration: {max(durations):.3f}s")

        if self.errors:
            print(f"\n⚠️  Errors:")
            error_types = defaultdict(int)
            for error in self.errors[:10]:  # Show first 10
                error_type = error.get("error", f"HTTP {error.get('status_code', 'Unknown')}")
                error_types[error_type] += 1

            for error_type, count in error_types.items():
                print(f"  {error_type}: {count}")

        # System resources
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        print(f"\nFinal System Resources:")
        print(f"  CPU: {cpu}%")
        print(f"  Memory: {memory}%")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Stress test Prismind services")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base API URL")
    parser.add_argument("--max-concurrent", type=int, default=100, help="Max concurrent requests")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--burst-size", type=int, default=500, help="Burst test size")

    args = parser.parse_args()

    print("=" * 60)
    print("Prismind Stress Test")
    print("=" * 60)
    print(f"Base URL: {args.base_url}")
    print(f"Max Concurrent: {args.max_concurrent}")
    print(f"Duration: {args.duration}s")
    print("\n⚠️  WARNING: This will put high load on the system!")
    print("   Press Ctrl+C to stop early\n")

    tester = StressTest(args.base_url)

    try:
        # Test 1: Ramp-up test
        tester.ramp_up_test("/health", args.max_concurrent, args.duration // 3)

        # Test 2: Sustained load
        endpoints = ["/health", "/health/ready", "/health/metrics"]
        tester.sustained_load_test(endpoints, args.max_concurrent // 2, args.duration // 2)

        # Test 3: Burst test
        tester.burst_test("/health", args.burst_size)

        # Test 4: Resource exhaustion
        tester.resource_exhaustion_test("/health")

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    finally:
        tester.print_summary()

    return 0


if __name__ == "__main__":
    exit(main())






