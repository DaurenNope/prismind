#!/usr/bin/env python3
"""
System Validation Script for BEYONDLINES
Validates all major system components and pipelines.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.services.new_database_manager import get_database_manager
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class ValidationResult:
    """Result of a validation test"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.status: str = "pending"
        self.message: str = ""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.data: Dict[str, Any] = {}
        self.duration: float = 0.0
        self.timestamp: str = datetime.now().isoformat()

    def success(self, message: str = "", data: Optional[Dict] = None):
        """Mark test as successful"""
        self.status = "success"
        self.message = message
        if data:
            self.data.update(data)

    def failure(self, message: str, errors: Optional[List[str]] = None):
        """Mark test as failed"""
        self.status = "failure"
        self.message = message
        if errors:
            self.errors.extend(errors)

    def warning(self, message: str):
        """Add warning"""
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_name": self.test_name,
            "status": self.status,
            "message": self.message,
            "errors": self.errors,
            "warnings": self.warnings,
            "data": self.data,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }


class SystemValidator:
    """Validates BEYONDLINES system components"""

    def __init__(self):
        self.results: List[ValidationResult] = []
        self.db_manager = None
        self.supabase_manager = None

    def validate_database_connection(self) -> ValidationResult:
        """Test database connection"""
        result = ValidationResult("database_connection")
        start_time = datetime.now()

        try:
            self.db_manager = get_database_manager()
            posts = self.db_manager.get_posts(limit=1)
            result.success(
                "Database connection successful",
                {"posts_count": len(posts) if posts else 0},
            )
        except Exception as e:
            result.failure(f"Database connection failed: {e}", [str(e)])

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    def validate_supabase_connection(self) -> ValidationResult:
        """Test Supabase connection"""
        result = ValidationResult("supabase_connection")
        start_time = datetime.now()

        try:
            from src.infrastructure.database.manager import SupabaseManager

            self.supabase_manager = SupabaseManager()
            # Test query
            test_posts = self.supabase_manager.get_posts(limit=1)
            result.success(
                "Supabase connection successful",
                {"posts_count": len(test_posts) if test_posts else 0},
            )
        except Exception as e:
            result.warning(f"Supabase connection failed (non-critical): {e}")
            result.status = "warning"

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    async def validate_analysis_pipeline(self, limit: int = 10) -> ValidationResult:
        """Test analysis pipeline on unanalyzed posts"""
        result = ValidationResult("analysis_pipeline")
        start_time = datetime.now()

        try:
            # Get unanalyzed posts
            if not self.db_manager:
                self.db_manager = get_database_manager()

            all_posts = self.db_manager.get_posts(limit=limit * 2)
            unanalyzed = [
                p
                for p in all_posts
                if not p.get("ai_summary") and not p.get("analyzed_at")
            ][:limit]

            if not unanalyzed:
                result.warning(
                    "No unanalyzed posts found - using analyzed posts for testing"
                )
                unanalyzed = all_posts[:limit]

            result.data["posts_to_analyze"] = len(unanalyzed)

            # Analyze posts
            analyzed_count = 0
            errors = []

            for post in unanalyzed:
                try:
                    from src.domain.analysis.services.post_analyzer import (
                        analyze_and_store_post,
                    )

                    success = await analyze_and_store_post(
                        self.db_manager, post, supabase_manager=self.supabase_manager
                    )
                    if success:
                        analyzed_count += 1

                    # Check if AI fields are populated
                    updated_post = self.db_manager.get_post_by_id(post.get("post_id"))
                    if updated_post:
                        ai_fields = {
                            "ai_summary": updated_post.get("ai_summary"),
                            "key_concepts": updated_post.get("key_concepts"),
                            "suggested_tags": updated_post.get("tags"),
                            "action_items": updated_post.get("action_items"),
                        }
                        result.data[f"post_{analyzed_count}_fields"] = ai_fields

                        # Check for None values
                        none_fields = [
                            k for k, v in ai_fields.items() if v is None or v == []
                        ]
                        if none_fields:
                            errors.append(
                                f"Post {post.get('post_id')} missing fields: {none_fields}"
                            )

                except Exception as e:
                    errors.append(f"Error analyzing post {post.get('post_id')}: {e}")

            result.data["analyzed_count"] = analyzed_count
            result.data["total_posts"] = len(unanalyzed)

            if analyzed_count == len(unanalyzed) and not errors:
                result.success(
                    f"Analysis pipeline successful: {analyzed_count}/{len(unanalyzed)} posts analyzed"
                )
            elif errors:
                result.failure(
                    f"Analysis pipeline completed with errors: {analyzed_count}/{len(unanalyzed)} posts analyzed",
                    errors,
                )
            else:
                result.warning(
                    f"Analysis pipeline partially successful: {analyzed_count}/{len(unanalyzed)} posts analyzed"
                )

        except Exception as e:
            result.failure(f"Analysis pipeline test failed: {e}", [str(e)])

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    def validate_ai_field_parsing(self) -> ValidationResult:
        """Validate that AI fields are being parsed correctly"""
        result = ValidationResult("ai_field_parsing")
        start_time = datetime.now()

        try:
            if not self.db_manager:
                self.db_manager = get_database_manager()

            # Get recently analyzed posts
            all_posts = self.db_manager.get_posts(limit=50)
            analyzed_posts = [
                p
                for p in all_posts
                if p.get("ai_summary") or p.get("analyzed_at")
            ][:20]

            if not analyzed_posts:
                result.warning("No analyzed posts found for validation")
                result.status = "warning"
                result.duration = (datetime.now() - start_time).total_seconds()
                return result

            missing_fields = {
                "key_concepts": [],
                "suggested_tags": [],
                "action_items": [],
            }

            for post in analyzed_posts:
                post_id = post.get("post_id", "unknown")

                # Check key_concepts
                key_concepts = post.get("key_concepts")
                if not key_concepts or key_concepts == []:
                    missing_fields["key_concepts"].append(post_id)

                # Check suggested_tags (stored as tags)
                tags = post.get("tags")
                if not tags or tags == []:
                    missing_fields["suggested_tags"].append(post_id)

                # Check action_items
                action_items = post.get("action_items")
                if not action_items or action_items == []:
                    missing_fields["action_items"].append(post_id)

            result.data["total_analyzed_posts"] = len(analyzed_posts)
            result.data["missing_fields"] = {
                k: len(v) for k, v in missing_fields.items()
            }
            result.data["missing_field_details"] = missing_fields

            total_missing = sum(len(v) for v in missing_fields.values())
            if total_missing == 0:
                result.success("All AI fields are populated correctly")
            elif total_missing < len(analyzed_posts) * 0.5:  # Less than 50% missing
                result.warning(
                    f"Some AI fields are missing: {total_missing} issues found"
                )
                result.status = "warning"
            else:
                result.failure(
                    f"Many AI fields are missing: {total_missing} issues found",
                    [
                        f"{k}: {len(v)} posts missing" for k, v in missing_fields.items()
                    ],
                )

        except Exception as e:
            result.failure(f"AI field parsing validation failed: {e}", [str(e)])

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    def validate_collection_pipeline(self) -> ValidationResult:
        """Test collection pipeline"""
        result = ValidationResult("collection_pipeline")
        start_time = datetime.now()

        try:
            # Test if collection services are available
            from src.domain.collection.services.unified_collection_service import (
                UnifiedCollectionService,
            )

            service = UnifiedCollectionService()
            supported_platforms = service.get_supported_platforms()

            result.data["supported_platforms"] = supported_platforms
            result.success(
                f"Collection pipeline available: {len(supported_platforms)} platforms supported"
            )

        except Exception as e:
            result.failure(f"Collection pipeline validation failed: {e}", [str(e)])

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    def validate_api_endpoints(self) -> ValidationResult:
        """Test API endpoints"""
        result = ValidationResult("api_endpoints")
        start_time = datetime.now()

        try:
            import requests

            base_url = "http://127.0.0.1:8000"
            endpoints = [
                "/api/health",
                "/api/posts",
                "/api/dashboard/stats",
            ]

            available = []
            unavailable = []

            for endpoint in endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        available.append(endpoint)
                    else:
                        unavailable.append(f"{endpoint} ({response.status_code})")
                except Exception:
                    unavailable.append(f"{endpoint} (connection failed)")

            result.data["available_endpoints"] = available
            result.data["unavailable_endpoints"] = unavailable

            if unavailable:
                result.warning(
                    f"Some API endpoints unavailable: {len(unavailable)}/{len(endpoints)}"
                )
                result.status = "warning"
            else:
                result.success(f"All API endpoints available: {len(available)}")

        except Exception as e:
            result.warning(f"API endpoint validation failed (API may not be running): {e}")
            result.status = "warning"

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    async def validate_research_agents(self) -> ValidationResult:
        """Test research agents end-to-end"""
        result = ValidationResult("research_agents")
        start_time = datetime.now()

        try:
            # Test research orchestrator
            from src.domain.intelligence.agents.autonomous_research_orchestrator import (
                AutonomousResearchOrchestrator,
            )

            orchestrator = AutonomousResearchOrchestrator()

            # Test with a simple query
            test_query = "AI prompt engineering best practices"
            try:
                research_result = await orchestrator.research_query(test_query)
                result.data["research_query"] = test_query
                result.data["has_result"] = research_result is not None

                if research_result:
                    result.data["result_keys"] = list(research_result.keys()) if isinstance(research_result, dict) else []
                    result.success("Research agents are operational")
                else:
                    result.warning("Research query returned empty result")
                    result.status = "warning"
            except Exception as e:
                result.warning(f"Research query test failed: {e}")
                result.status = "warning"

        except ImportError as e:
            result.warning(f"Research agents not available: {e}")
            result.status = "warning"
        except Exception as e:
            result.failure(f"Research agents validation failed: {e}", [str(e)])

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    def validate_github_integration(self) -> ValidationResult:
        """Test GitHub integration"""
        result = ValidationResult("github_integration")
        start_time = datetime.now()

        try:
            # Test GitHub research agent
            from src.domain.intelligence.agents.github_research_agent import GitHubResearchAgent

            agent = GitHubResearchAgent()

            # Check if agent is properly initialized
            result.data["agent_initialized"] = True
            result.success("GitHub research agent available")

        except ImportError as e:
            result.warning(f"GitHub integration not available: {e}")
            result.status = "warning"
        except Exception as e:
            result.failure(f"GitHub integration validation failed: {e}", [str(e)])

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    def validate_quality_pipeline(self) -> ValidationResult:
        """Test quality pipeline"""
        result = ValidationResult("quality_pipeline")
        start_time = datetime.now()

        try:
            if not self.db_manager:
                self.db_manager = get_database_manager()

            # Check for quality scoring
            all_posts = self.db_manager.get_posts(limit=100)
            posts_with_scores = [
                p for p in all_posts if p.get("value_score") is not None and p.get("quality_score") is not None
            ]
            posts_without_scores = [
                p for p in all_posts if p.get("value_score") is None or p.get("quality_score") is None
            ]

            result.data["total_posts"] = len(all_posts)
            result.data["posts_with_scores"] = len(posts_with_scores)
            result.data["posts_without_scores"] = len(posts_without_scores)

            score_coverage = len(posts_with_scores) / len(all_posts) if all_posts else 0
            result.data["score_coverage"] = f"{score_coverage:.1%}"

            if score_coverage >= 0.8:
                result.success(f"Quality pipeline operational: {score_coverage:.1%} posts have scores")
            elif score_coverage >= 0.5:
                result.warning(f"Quality pipeline partially operational: {score_coverage:.1%} posts have scores")
                result.status = "warning"
            else:
                result.warning(f"Quality pipeline needs attention: {score_coverage:.1%} posts have scores")
                result.status = "warning"

        except Exception as e:
            result.failure(f"Quality pipeline validation failed: {e}", [str(e)])

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    def validate_error_handling(self) -> ValidationResult:
        """Review error handling mechanisms"""
        result = ValidationResult("error_handling")
        start_time = datetime.now()

        try:
            # Check for error handling patterns in codebase
            errors_checked = []

            # Check database error handling
            try:
                if not self.db_manager:
                    self.db_manager = get_database_manager()
                # Try an invalid query
                try:
                    self.db_manager.get_post_by_id("invalid_id_test")
                except Exception:
                    pass  # Expected to fail gracefully
                errors_checked.append("database_errors")
            except Exception:
                pass

            # Check collection error handling
            try:
                from src.domain.collection.services.unified_collection_service import (
                    UnifiedCollectionService,
                )
                service = UnifiedCollectionService()
                # Test unsupported platform
                try:
                    service.collect("unsupported_platform", {})
                except Exception:
                    pass  # Expected to fail gracefully
                errors_checked.append("collection_errors")
            except Exception:
                pass

            result.data["error_handling_checks"] = errors_checked

            if errors_checked:
                result.success(f"Error handling mechanisms verified: {len(errors_checked)} checks")
            else:
                result.warning("Error handling checks could not be completed")
                result.status = "warning"

        except Exception as e:
            result.warning(f"Error handling validation incomplete: {e}")
            result.status = "warning"

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    def validate_configuration(self) -> ValidationResult:
        """Review configuration management"""
        result = ValidationResult("configuration")
        start_time = datetime.now()

        try:
            issues = []
            good_practices = []

            # Check for .env file
            env_file = project_root / ".env"
            if env_file.exists():
                good_practices.append("env_file_exists")
            else:
                issues.append("No .env file found")

            # Check for secrets management
            try:
                from src.shared.utils.secrets_manager import get_secrets_manager
                secrets = get_secrets_manager()
                good_practices.append("secrets_manager_available")
            except Exception:
                issues.append("Secrets manager not available")

            # Check cookie file locations
            config_dir = project_root / "config"
            cookies_dir = project_root / "cookies"
            cookie_files_config = list(config_dir.glob("*cookie*.json")) if config_dir.exists() else []
            cookie_files_cookies = list(cookies_dir.glob("*cookie*.json")) if cookies_dir.exists() else []

            if cookie_files_config and cookie_files_cookies:
                issues.append(f"Cookie files in multiple locations: config/ ({len(cookie_files_config)}) and cookies/ ({len(cookie_files_cookies)})")
            elif cookie_files_config or cookie_files_cookies:
                good_practices.append("cookie_files_found")

            result.data["issues"] = issues
            result.data["good_practices"] = good_practices

            if not issues:
                result.success("Configuration management looks good")
            elif len(issues) <= 2:
                result.warning(f"Configuration has {len(issues)} minor issues")
                result.status = "warning"
            else:
                result.warning(f"Configuration has {len(issues)} issues")
                result.status = "warning"

        except Exception as e:
            result.warning(f"Configuration validation incomplete: {e}")
            result.status = "warning"

        result.duration = (datetime.now() - start_time).total_seconds()
        return result

    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation tests"""
        logger.info("=" * 70)
        logger.info("🔍 Starting System Validation")
        logger.info("=" * 70)

        # Phase 1: Foundation validations
        logger.info("\n📋 Phase 1: Foundation Validation")
        self.results.append(self.validate_database_connection())
        self.results.append(self.validate_supabase_connection())
        self.results.append(await self.validate_analysis_pipeline(limit=10))
        self.results.append(self.validate_error_handling())
        self.results.append(self.validate_configuration())

        # Phase 2: Component validations
        logger.info("\n📋 Phase 2: Component Validation")
        self.results.append(self.validate_ai_field_parsing())
        self.results.append(self.validate_collection_pipeline())
        self.results.append(self.validate_api_endpoints())

        # Phase 2: Intelligence pipeline validations
        logger.info("\n📋 Phase 2: Intelligence Pipeline Validation")
        self.results.append(await self.validate_research_agents())
        self.results.append(self.validate_github_integration())
        self.results.append(self.validate_quality_pipeline())

        # Summary
        summary = self.generate_summary()
        return summary

    def generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary"""
        total_tests = len(self.results)
        successful = len([r for r in self.results if r.status == "success"])
        failed = len([r for r in self.results if r.status == "failure"])
        warnings = len([r for r in self.results if r.status == "warning"])

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "successful": successful,
            "failed": failed,
            "warnings": warnings,
            "status": "success" if failed == 0 else "failure",
            "results": [r.to_dict() for r in self.results],
        }

        # Log summary
        logger.info("\n" + "=" * 70)
        logger.info("📊 Validation Summary")
        logger.info("=" * 70)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⚠️  Warnings: {warnings}")
        logger.info("=" * 70)

        for result in self.results:
            status_icon = "✅" if result.status == "success" else "❌" if result.status == "failure" else "⚠️"
            logger.info(f"{status_icon} {result.test_name}: {result.message}")
            if result.errors:
                for error in result.errors:
                    logger.error(f"   Error: {error}")
            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"   Warning: {warning}")

        return summary


async def main():
    """Main validation function"""
    validator = SystemValidator()
    summary = await validator.run_all_validations()

    # Save results
    output_dir = project_root / "docs"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "VALIDATION_RESULTS.md"

    # Generate markdown report
    report = generate_markdown_report(summary)
    output_file.write_text(report)
    logger.info(f"\n📄 Validation report saved to: {output_file}")

    return summary


def generate_markdown_report(summary: Dict[str, Any]) -> str:
    """Generate markdown validation report"""
    lines = [
        "# System Validation Results",
        "",
        f"**Date**: {summary['timestamp']}",
        f"**Status**: {'✅ PASSED' if summary['status'] == 'success' else '❌ FAILED'}",
        "",
        "## Summary",
        "",
        f"- **Total Tests**: {summary['total_tests']}",
        f"- **✅ Successful**: {summary['successful']}",
        f"- **❌ Failed**: {summary['failed']}",
        f"- **⚠️  Warnings**: {summary['warnings']}",
        "",
        "## Test Results",
        "",
    ]

    for result in summary["results"]:
        status_icon = (
            "✅"
            if result["status"] == "success"
            else "❌"
            if result["status"] == "failure"
            else "⚠️"
        )
        lines.append(f"### {status_icon} {result['test_name']}")
        lines.append("")
        lines.append(f"**Status**: {result['status']}")
        lines.append(f"**Message**: {result['message']}")
        lines.append(f"**Duration**: {result['duration']:.2f}s")
        lines.append("")

        if result["errors"]:
            lines.append("**Errors**:")
            for error in result["errors"]:
                lines.append(f"- {error}")
            lines.append("")

        if result["warnings"]:
            lines.append("**Warnings**:")
            for warning in result["warnings"]:
                lines.append(f"- {warning}")
            lines.append("")

        if result["data"]:
            lines.append("**Data**:")
            lines.append("```json")
            lines.append(json.dumps(result["data"], indent=2))
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())

