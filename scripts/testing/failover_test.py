#!/usr/bin/env python3
"""
Failover Test Script for Prismind
===================================

Tests system behavior under failure scenarios:
- Database failover
- Service restart
- Network issues
- Resource exhaustion

Usage:
    python scripts/testing/failover_test.py
    python scripts/testing/failover_test.py --scenario database
"""

import argparse
import subprocess
import time
from typing import Dict, List

import httpx

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class FailoverTest:
    """Failover test runner"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: List[Dict] = []

    def check_health(self) -> Dict:
        """Check system health"""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                return {
                    "status": response.status_code,
                    "healthy": response.status_code == 200,
                    "data": response.json() if response.status_code == 200 else None,
                }
        except Exception as e:
            return {"status": 0, "healthy": False, "error": str(e)}

    def test_service_restart(self, service: str):
        """Test service restart scenario"""
        print(f"\n🔄 Testing service restart: {service}")

        # Check initial health
        initial_health = self.check_health()
        print(f"   Initial health: {'✓' if initial_health['healthy'] else '✗'}")

        # Restart service
        print(f"   Restarting {service}...")
        try:
            subprocess.run(
                ["docker", "compose", "restart", service],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Failed to restart: {e}")
            return

        # Wait for restart
        print(f"   Waiting for restart (30s)...")
        time.sleep(30)

        # Check health during and after restart
        recovery_times = []
        for i in range(10):  # Check every 3s for 30s
            time.sleep(3)
            health = self.check_health()
            if health["healthy"]:
                recovery_times.append(i * 3)
                print(f"   ✓ Service recovered after ~{i * 3}s")
                break
            else:
                print(f"   ⏳ Still recovering... ({i * 3}s)")

        # Final health check
        final_health = self.check_health()
        print(f"   Final health: {'✓' if final_health['healthy'] else '✗'}")

        self.results.append({
            "test": f"service_restart_{service}",
            "initial_healthy": initial_health["healthy"],
            "final_healthy": final_health["healthy"],
            "recovery_time": recovery_times[0] if recovery_times else None,
            "success": final_health["healthy"],
        })

    def test_database_failover(self):
        """Test database connection failure"""
        print(f"\n🗄️  Testing database failover")

        # Check initial health
        initial_health = self.check_health()
        print(f"   Initial health: {'✓' if initial_health['healthy'] else '✗'}")

        # Simulate database failure (stop database connection in docker-compose)
        print(f"   Simulating database failure...")
        print(f"   ⚠️  Manual test: Stop Supabase connection or network issue")

        # Monitor system behavior
        print(f"   Monitoring system for 60s...")
        degraded_count = 0
        for i in range(20):  # Check every 3s for 60s
            time.sleep(3)
            health = self.check_health()

            if health.get("data") and health["data"].get("status") == "degraded":
                degraded_count += 1
                print(f"   ⚠️  System degraded ({degraded_count}x)")

            if not health["healthy"]:
                print(f"   ✗ System unhealthy")

        print(f"   System handled failure gracefully: {degraded_count > 0}")

    def test_redis_failover(self):
        """Test Redis connection failure"""
        print(f"\n📦 Testing Redis failover")

        # Check initial health
        initial_health = self.check_health()
        print(f"   Initial health: {'✓' if initial_health['healthy'] else '✗'}")

        # Restart Redis
        print(f"   Restarting Redis...")
        try:
            subprocess.run(
                ["docker", "compose", "restart", "redis"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Failed to restart Redis: {e}")
            return

        # Monitor during Redis restart
        print(f"   Monitoring during Redis restart (15s)...")
        for i in range(5):
            time.sleep(3)
            health = self.check_health()
            status = "✓" if health["healthy"] else "✗"
            print(f"   {status} Health check {i + 1}/5")

        # Final check
        final_health = self.check_health()
        print(f"   Final health: {'✓' if final_health['healthy'] else '✗'}")

        self.results.append({
            "test": "redis_failover",
            "initial_healthy": initial_health["healthy"],
            "final_healthy": final_health["healthy"],
            "success": final_health["healthy"],
        })

    def test_concurrent_failures(self):
        """Test multiple concurrent failures"""
        print(f"\n💥 Testing concurrent failures")

        # Check initial health
        initial_health = self.check_health()
        print(f"   Initial health: {'✓' if initial_health['healthy'] else '✗'}")

        # Restart multiple services simultaneously
        services = ["redis", "api"]
        print(f"   Restarting multiple services: {', '.join(services)}")

        try:
            subprocess.run(
                ["docker", "compose", "restart"] + services,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Failed to restart services: {e}")
            return

        # Monitor recovery
        print(f"   Monitoring recovery (60s)...")
        recovery_start = time.time()

        for i in range(20):
            time.sleep(3)
            health = self.check_health()

            if health["healthy"]:
                recovery_time = time.time() - recovery_start
                print(f"   ✓ System recovered after {recovery_time:.1f}s")
                break
            else:
                print(f"   ⏳ Still recovering... ({i * 3}s)")

        final_health = self.check_health()
        recovery_time = time.time() - recovery_start if final_health["healthy"] else None

        print(f"   Final health: {'✓' if final_health['healthy'] else '✗'}")
        if recovery_time:
            print(f"   Recovery time: {recovery_time:.1f}s")

        self.results.append({
            "test": "concurrent_failures",
            "initial_healthy": initial_health["healthy"],
            "final_healthy": final_health["healthy"],
            "recovery_time": recovery_time,
            "success": final_health["healthy"],
        })

    def test_network_partition(self):
        """Test network partition scenario"""
        print(f"\n🌐 Testing network partition (simulated)")

        print(f"   ⚠️  Manual test: Disconnect network or block ports")
        print(f"   Expected: System should degrade gracefully")

        # Monitor health during network issues
        print(f"   Monitoring for 30s...")
        for i in range(10):
            time.sleep(3)
            health = self.check_health()
            status = "✗" if not health["healthy"] else "⚠️" if health.get("data", {}).get("status") == "degraded" else "✓"
            print(f"   {status} Health check {i + 1}/10")

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("Failover Test Summary")
        print(f"{'='*60}")

        if not self.results:
            print("No automated tests completed")
            return

        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])

        print(f"Tests Run:       {total}")
        print(f"Successful:      {successful}")
        print(f"Failed:          {total - successful}")
        print(f"Success Rate:    {successful / total * 100:.1f}%")

        print(f"\nTest Details:")
        for result in self.results:
            status = "✓" if result["success"] else "✗"
            recovery = f" (recovery: {result['recovery_time']:.1f}s)" if result.get("recovery_time") else ""
            print(f"  {status} {result['test']}{recovery}")

        if successful < total:
            print(f"\n⚠️  Some tests failed - review system resilience")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Failover test Prismind services")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base API URL")
    parser.add_argument(
        "--scenario",
        choices=["all", "service", "database", "redis", "concurrent", "network"],
        default="all",
        help="Test scenario to run",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Prismind Failover Test")
    print("=" * 60)
    print(f"Base URL: {args.base_url}")
    print(f"Scenario: {args.scenario}")
    print("\n⚠️  WARNING: This will restart services!")
    print("   Make sure you're in a test environment\n")

    tester = FailoverTest(args.base_url)

    try:
        if args.scenario in ["all", "service"]:
            tester.test_service_restart("api")
            tester.test_service_restart("api-gateway")

        if args.scenario in ["all", "database"]:
            tester.test_database_failover()

        if args.scenario in ["all", "redis"]:
            tester.test_redis_failover()

        if args.scenario in ["all", "concurrent"]:
            tester.test_concurrent_failures()

        if args.scenario in ["all", "network"]:
            tester.test_network_partition()

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    finally:
        tester.print_summary()

    return 0


if __name__ == "__main__":
    exit(main())






