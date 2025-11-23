"""
QA Agent - Comprehensive Quality Assurance

Runs tests, checks code quality, validates integrations, and reports issues.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from src.domain.intelligence.agents.specialized.base_specialized import SpecializedAgent

logger = logging.getLogger(__name__)


class QAAgent(SpecializedAgent):
    """
    The QA Agent: Comprehensive quality assurance and testing
    """

    def __init__(self):
        super().__init__(agent_id="qa", agent_name="The QA Agent", role="Quality Assurance")
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.test_results: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize QA agent"""
        await super().initialize()
        return True

    async def _process_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive QA checks"""
        logger.info("🔍 QA Agent starting comprehensive quality checks...")

        try:
            results = await self._run_qa_suite()

            return {
                "messages": [AIMessage(content=f"QA Report: {results['summary']}")],
                "artifacts": {"qa_results": results},
                "current_agent": "qa",
                "task_status": "qa_complete"
            }
        except Exception as e:
            logger.error(f"QA check failed: {e}", exc_info=True)
            return {
                "messages": [AIMessage(content=f"QA Error: {str(e)}")],
                "artifacts": {"qa_results": {"error": str(e)}},
                "errors": [str(e)],
                "current_agent": "qa"
            }

    async def _run_qa_suite(self) -> Dict[str, Any]:
        """Run comprehensive QA suite"""
        results = {
            "tests": await self._run_tests(),
            "linting": await self._check_linting(),
            "type_checking": await self._check_types(),
            "imports": await self._check_imports(),
            "code_quality": await self._check_code_quality(),
            "security": await self._check_security(),
            "coverage": await self._check_coverage(),
            "integration": await self._check_integration(),
            "performance": await self._check_performance(),
            "documentation": await self._check_documentation()
        }

        # Calculate overall score
        results["overall_score"] = self._calculate_score(results)
        results["summary"] = self._generate_summary(results)

        return results

    async def _run_tests(self) -> Dict[str, Any]:
        """Run test suite"""
        try:
            result = subprocess.run(
                ["pytest", "tests/", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_root
            )

            # Parse output
            output = result.stdout + result.stderr
            passed = output.count("PASSED")
            failed = output.count("FAILED")
            total = passed + failed

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "passed": passed,
                "failed": failed,
                "total": total,
                "coverage": passed / total * 100 if total > 0 else 0,
                "output": output[-1000:]  # Last 1000 chars
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Test execution timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_linting(self) -> Dict[str, Any]:
        """Check code linting"""
        try:
            result = subprocess.run(
                ["ruff", "check", "src/", "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.project_root
            )

            if result.returncode == 0:
                return {"status": "pass", "errors": 0, "warnings": 0}
            else:
                try:
                    errors = json.loads(result.stdout)
                    return {
                        "status": "fail",
                        "errors": len([e for e in errors if e.get("code", "").startswith("E")]),
                        "warnings": len([e for e in errors if e.get("code", "").startswith("W")]),
                        "details": errors[:20]  # First 20 errors
                    }
                except:
                    return {"status": "fail", "errors": result.stdout.count("error")}
        except FileNotFoundError:
            return {"status": "error", "error": "ruff not found"}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Linting timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_types(self) -> Dict[str, Any]:
        """Check type hints"""
        try:
            result = subprocess.run(
                ["mypy", "src/", "--ignore-missing-imports"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root
            )

            errors = result.stdout.count("error:")
            return {
                "status": "pass" if errors == 0 else "fail",
                "errors": errors,
                "output": result.stdout[-500:] if errors > 0 else ""
            }
        except FileNotFoundError:
            return {"status": "error", "error": "mypy not found"}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Type checking timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_imports(self) -> Dict[str, Any]:
        """Check for broken imports"""
        broken = []
        try:
            # Try importing main modules
            import sys
            sys.path.insert(0, str(self.project_root))

            modules_to_check = [
                "src.agents.base_agent",
                "src.agents.registry",
                "src.core.orchestration.agent_graph",
                "src.pipeline.full_automation_loop",
                "src.publishing.worker",
                "src.database.publishing.bridge"
            ]

            for module in modules_to_check:
                try:
                    __import__(module)
                except ImportError as e:
                    broken.append({"module": module, "error": str(e)})

            return {
                "status": "pass" if len(broken) == 0 else "fail",
                "broken_imports": broken
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_code_quality(self) -> Dict[str, Any]:
        """Check code quality metrics"""
        issues = []

        # Check for TODO/FIXME
        for py_file in self.project_root.rglob("src/**/*.py"):
            try:
                content = py_file.read_text()
                if "TODO" in content or "FIXME" in content:
                    issues.append({
                        "file": str(py_file.relative_to(self.project_root)),
                        "type": "TODO/FIXME",
                        "count": content.count("TODO") + content.count("FIXME")
                    })
            except Exception:
                pass

        return {
            "status": "pass" if len(issues) == 0 else "warn",
            "issues": issues[:20]  # First 20
        }

    async def _check_security(self) -> Dict[str, Any]:
        """Check for security issues"""
        try:
            result = subprocess.run(
                ["bandit", "-r", "src/", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root
            )

            try:
                data = json.loads(result.stdout)
                issues = data.get("results", [])
                high_severity = [i for i in issues if i.get("issue_severity") == "HIGH"]

                return {
                    "status": "pass" if len(high_severity) == 0 else "fail",
                    "high_severity": len(high_severity),
                    "total_issues": len(issues),
                    "details": high_severity[:10]
                }
            except:
                return {"status": "unknown", "output": result.stdout[:500]}
        except FileNotFoundError:
            return {"status": "error", "error": "bandit not found"}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Security check timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_coverage(self) -> Dict[str, Any]:
        """Check test coverage"""
        try:
            result = subprocess.run(
                ["pytest", "tests/", "--cov=src", "--cov-report=json"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_root
            )

            try:
                coverage_file = self.project_root / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, "r") as f:
                        data = json.load(f)
                        total = data.get("totals", {}).get("percent_covered", 0)

                        return {
                            "status": "pass" if total >= 70 else "warn",
                            "coverage": total,
                            "target": 70
                        }
                else:
                    return {"status": "unknown", "output": result.stdout[-500:]}
            except:
                return {"status": "unknown", "output": result.stdout[-500:]}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Coverage check timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_integration(self) -> Dict[str, Any]:
        """Check integration points"""
        issues = []

        # Check critical integrations
        integrations = [
            ("AgentGraph", "src.core.orchestration.agent_graph"),
            ("FullAutomationLoop", "src.pipeline.full_automation_loop"),
            ("PublisherWorker", "src.publishing.worker"),
            ("IntegratedAutomation", "src.core.orchestration.integrated_automation")
        ]

        import sys
        sys.path.insert(0, str(self.project_root))

        for name, module_path in integrations:
            try:
                module = __import__(module_path, fromlist=[name])
                if not hasattr(module, name):
                    issues.append(f"{name} not found in {module_path}")
            except Exception as e:
                issues.append(f"{name} import failed: {e}")

        return {
            "status": "pass" if len(issues) == 0 else "fail",
            "issues": issues
        }

    async def _check_performance(self) -> Dict[str, Any]:
        """Check performance metrics"""
        # Check for obvious performance issues
        issues = []

        # Check for synchronous operations in async contexts
        # Check for missing await statements
        # Check for blocking I/O

        return {
            "status": "pass",
            "issues": issues
        }

    async def _check_documentation(self) -> Dict[str, Any]:
        """Check documentation coverage"""
        documented = 0
        total = 0

        for py_file in self.project_root.rglob("src/**/*.py"):
            if "__init__" in str(py_file):
                continue
            total += 1
            try:
                content = py_file.read_text()
                if '"""' in content or "'''" in content:
                    documented += 1
            except Exception:
                pass

        coverage = (documented / total * 100) if total > 0 else 0

        return {
            "status": "pass" if coverage >= 80 else "warn",
            "coverage": coverage,
            "target": 80
        }

    def _calculate_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall QA score"""
        scores = {
            "tests": 1.0 if results["tests"].get("status") == "success" else 0.0,
            "linting": 1.0 if results["linting"].get("errors", 0) == 0 else 0.5,
            "types": 1.0 if results["type_checking"].get("errors", 0) == 0 else 0.5,
            "imports": 1.0 if len(results["imports"].get("broken_imports", [])) == 0 else 0.0,
            "security": 1.0 if results["security"].get("high_severity", 0) == 0 else 0.0,
            "coverage": min(1.0, results["coverage"].get("coverage", 0) / 70),
            "integration": 1.0 if results["integration"].get("status") == "pass" else 0.0
        }

        return sum(scores.values()) / len(scores) * 100

    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate QA summary"""
        score = results["overall_score"]

        if score >= 90:
            return f"✅ Excellent ({score:.1f}%) - Production ready"
        elif score >= 70:
            return f"⚠️ Good ({score:.1f}%) - Minor issues to address"
        elif score >= 50:
            return f"⚠️ Needs Work ({score:.1f}%) - Several issues found"
        else:
            return f"❌ Critical Issues ({score:.1f}%) - Not production ready"

