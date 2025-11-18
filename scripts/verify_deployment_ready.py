#!/usr/bin/env python3
"""
BEYONDLINES Deployment Readiness Verification
===========================================

Comprehensive verification that the BEYONDLINES system is ready for deployment.
Tests Docker configuration, health endpoints, and critical dependencies.

Author: BEYONDLINES AI System
"""

import asyncio
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

# Add src to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class DeploymentVerifier:
    """Comprehensive deployment verification tool"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "overall_status": "unknown",
        }

    def log_result(
        self, check_name: str, status: str, details: str = "", data: Any = None
    ):
        """Log verification result"""
        self.results["checks"][check_name] = {
            "status": status,  # PASS, FAIL, WARN
            "details": details,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

    def verify_docker_configuration(self):
        """Verify Docker Compose configuration"""
        print("🐳 Verifying Docker configuration...")

        try:
            # Check if docker-compose.yml exists
            compose_file = project_root / "docker-compose.yml"
            if not compose_file.exists():
                self.log_result("docker_config", "FAIL", "docker-compose.yml not found")
                return

            # Validate docker-compose configuration
            result = subprocess.run(
                ["docker-compose", "config", "--quiet"],
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.log_result(
                    "docker_config", "PASS", "Docker Compose configuration is valid"
                )
            else:
                self.log_result(
                    "docker_config",
                    "FAIL",
                    f"Docker Compose validation failed: {result.stderr}",
                )

        except FileNotFoundError:
            self.log_result("docker_config", "FAIL", "Docker Compose not installed")
        except Exception as e:
            self.log_result("docker_config", "FAIL", f"Docker verification error: {e}")

    def verify_required_files(self):
        """Verify required files exist"""
        print("📁 Verifying required files...")

        required_files = [
            "requirements.txt",
            "docker-compose.yml",
            "services/api/Dockerfile",
            "services/worker/Dockerfile",
            "services/gateway/Dockerfile",
            "services/api/app.py",
            "services/worker/run_worker.py",
            "src/api/main.py",
            ".env",
        ]

        missing_files = []
        for file_path in required_files:
            full_path = project_root / file_path
            if full_path.exists():
                self.log_result(
                    f"file_{file_path.replace('/', '_')}", "PASS", f"✓ {file_path}"
                )
            else:
                missing_files.append(file_path)
                self.log_result(
                    f"file_{file_path.replace('/', '_')}",
                    "FAIL",
                    f"✗ {file_path} missing",
                )

        if missing_files:
            self.log_result(
                "required_files",
                "FAIL",
                f"Missing {len(missing_files)} required files: {', '.join(missing_files)}",
            )
        else:
            self.log_result("required_files", "PASS", "All required files present")

    def verify_environment_variables(self):
        """Verify critical environment variables"""
        print("🔐 Verifying environment variables...")

        env_file = project_root / ".env"
        if not env_file.exists():
            self.log_result("env_file", "FAIL", ".env file not found")
            return

        # Load environment variables
        with open(env_file, "r") as f:
            env_content = f.read()

        critical_vars = [
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "REDIS_URL",
            "TWITTER_BEARER_TOKEN",
        ]

        missing_vars = []
        for var in critical_vars:
            if f"{var}=" in env_content:
                self.log_result(f"env_{var.lower()}", "PASS", f"✓ {var} configured")
            else:
                missing_vars.append(var)
                self.log_result(f"env_{var.lower()}", "WARN", f"⚠ {var} not configured")

        if missing_vars:
            self.log_result(
                "environment_vars",
                "WARN",
                f"Some environment variables missing: {', '.join(missing_vars)}",
            )
        else:
            self.log_result(
                "environment_vars", "PASS", "Critical environment variables configured"
            )

    def verify_python_imports(self):
        """Verify critical Python imports work"""
        print("🐍 Verifying Python imports...")

        critical_imports = [
            ("fastapi", "FastAPI web framework"),
            ("src.database.database_agent", "Database agent"),
            ("src.pipeline.orchestrator", "Main orchestrator"),
            ("src.utils.standardized_result", "Standardized results"),
            ("src.services.posting_service", "Posting service"),
            ("src.publishing.platforms.twitter_playwright", "Twitter platform"),
            ("src.publishing.platforms.threads_playwright", "Threads platform"),
        ]

        failed_imports = []
        for module, description in critical_imports:
            try:
                __import__(module)
                self.log_result(
                    f"import_{module.replace('.', '_')}", "PASS", f"✓ {description}"
                )
            except ImportError as e:
                failed_imports.append(f"{module}: {e}")
                self.log_result(
                    f"import_{module.replace('.', '_')}",
                    "FAIL",
                    f"✗ {description}: {e}",
                )

        if failed_imports:
            self.log_result(
                "python_imports", "FAIL", f"Failed imports: {len(failed_imports)}"
            )
        else:
            self.log_result("python_imports", "PASS", "All critical imports successful")

    def verify_service_configuration(self):
        """Verify service configurations"""
        print("⚙️ Verifying service configurations...")

        services_config = {
            "api": {"port": 8000, "dockerfile": "services/api/Dockerfile"},
            "api-gateway": {"port": 8080, "dockerfile": "services/gateway/Dockerfile"},
            "worker": {
                "dockerfile": "services/worker/Dockerfile",
                "entrypoint": "services/worker/run_worker.py",
            },
        }

        all_services_valid = True
        for service_name, config in services_config.items():
            dockerfile_path = project_root / config["dockerfile"]

            if dockerfile_path.exists():
                self.log_result(
                    f"service_{service_name}",
                    "PASS",
                    f"✓ {config['dockerfile']} exists",
                )

                # Check entrypoint for worker
                if service_name == "worker":
                    entrypoint_path = project_root / config["entrypoint"]
                    if entrypoint_path.exists():
                        self.log_result(
                            f"service_{service_name}_entrypoint",
                            "PASS",
                            f"✓ {config['entrypoint']} exists",
                        )
                    else:
                        self.log_result(
                            f"service_{service_name}_entrypoint",
                            "FAIL",
                            f"✗ {config['entrypoint']} missing",
                        )
                        all_services_valid = False
            else:
                self.log_result(
                    f"service_{service_name}",
                    "FAIL",
                    f"✗ {config['dockerfile']} missing",
                )
                all_services_valid = False

        if all_services_valid:
            self.log_result(
                "service_configuration", "PASS", "All service configurations valid"
            )
        else:
            self.log_result(
                "service_configuration", "FAIL", "Some service configurations missing"
            )

    def verify_health_endpoints(self):
        """Verify health endpoints in API services"""
        print("🏥 Verifying health endpoints...")

        # Check if health endpoints are defined in main API
        try:
            import src.api.main

            app = src.api.main.app

            health_routes = [
                route.path for route in app.routes if "health" in route.path.lower()
            ]
            if health_routes:
                self.log_result(
                    "health_endpoints",
                    "PASS",
                    f"✓ Found {len(health_routes)} health endpoints: {', '.join(health_routes)}",
                )
            else:
                self.log_result(
                    "health_endpoints",
                    "WARN",
                    "⚠ No health endpoints found in main API",
                )

        except Exception as e:
            self.log_result(
                "health_endpoints", "FAIL", f"✗ Could not verify health endpoints: {e}"
            )

    def calculate_overall_status(self):
        """Calculate overall deployment readiness status"""
        passed = sum(
            1 for check in self.results["checks"].values() if check["status"] == "PASS"
        )
        failed = sum(
            1 for check in self.results["checks"].values() if check["status"] == "FAIL"
        )
        warned = sum(
            1 for check in self.results["checks"].values() if check["status"] == "WARN"
        )
        total = len(self.results["checks"])

        if failed == 0:
            if warned == 0:
                self.results["overall_status"] = "READY"
            else:
                self.results["overall_status"] = "READY_WITH_WARNINGS"
        else:
            self.results["overall_status"] = "NOT_READY"

        self.results["summary"] = {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "warned": warned,
        }

    def generate_report(self):
        """Generate deployment readiness report"""
        print("\n" + "=" * 60)
        print("🚀 BEYONDLINES DEPLOYMENT READINESS REPORT")
        print("=" * 60)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Overall Status: {self.results['overall_status']}")

        if "summary" in self.results:
            summary = self.results["summary"]
            print(
                f"Checks: {summary['passed']}/{summary['total_checks']} passed, {summary['failed']} failed, {summary['warned']} warnings"
            )

        print("\n📋 Detailed Results:")
        print("-" * 40)

        for check_name, result in self.results["checks"].items():
            if check_name in ["timestamp", "summary", "overall_status"]:
                continue

            status_icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(
                result["status"], "❓"
            )

            print(f"{status_icon} {check_name}: {result['details']}")

            if result["data"] and isinstance(result["data"], dict):
                for key, value in result["data"].items():
                    if key != "timestamp":  # Skip redundant timestamp
                        print(f"    {key}: {value}")

        print("\n" + "=" * 60)

        if self.results["overall_status"] == "READY":
            print(
                "🎉 DEPLOYMENT READY! Your BEYONDLINES system is fully prepared for deployment."
            )
        elif self.results["overall_status"] == "READY_WITH_WARNINGS":
            print(
                "⚠️ DEPLOYMENT READY WITH WARNINGS! System is deployable but review warnings above."
            )
        else:
            print("❌ DEPLOYMENT NOT READY! Fix the failed checks before deploying.")

        print("=" * 60)

        return self.results["overall_status"]

    def run_verification(self):
        """Run all verification checks"""
        print("🔍 Starting BEYONDLINES deployment verification...")
        print()

        self.verify_docker_configuration()
        self.verify_required_files()
        self.verify_environment_variables()
        self.verify_python_imports()
        self.verify_service_configuration()
        self.verify_health_endpoints()

        self.calculate_overall_status()
        return self.generate_report()


def main():
    """Main verification function"""
    verifier = DeploymentVerifier()
    status = verifier.run_verification()

    # Return appropriate exit code
    if status == "READY":
        sys.exit(0)
    elif status == "READY_WITH_WARNINGS":
        sys.exit(0)  # Still deployable
    else:
        sys.exit(1)  # Not ready


if __name__ == "__main__":
    main()
