#!/usr/bin/env python3
"""
Comprehensive Mechanical Parts Validation
Tests all critical mechanical components before deployment.
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.details = {}
        self.warnings = []


def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(80)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")


def print_test(
    name: str, status: str, error: Optional[str] = None, details: Optional[Dict] = None
):
    if status == "PASS":
        print(f"{GREEN}✅ {name}: PASSED{RESET}")
    elif status == "FAIL":
        print(f"{RED}❌ {name}: FAILED{RESET}")
        if error:
            print(f"   {RED}Error: {error}{RESET}")
    elif status == "WARN":
        print(f"{YELLOW}⚠️  {name}: WARNING{RESET}")
        if error:
            print(f"   {YELLOW}Warning: {error}{RESET}")
    else:
        print(f"{BLUE}ℹ️  {name}: {status}{RESET}")

    if details:
        for key, value in details.items():
            print(f"   {BLUE}{key}: {value}{RESET}")


# ============================================================================
# TEST 1: ENVIRONMENT & IMPORTS
# ============================================================================


def test_imports() -> TestResult:
    """Test all critical imports"""
    result = TestResult("Imports")

    try:
        # Core database
        # Analysis
        from src.core.analysis.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )
        from src.core.extraction.reddit_extractor import RedditExtractor
        from src.core.extraction.threads_extractor import ThreadsExtractor
        from src.core.extraction.twitter_extractor_playwright import (
            TwitterExtractorPlaywright,
        )
        from src.database.database_agent import DatabaseAgent
        from src.database.manager import SupabaseManager

        # Collection
        from src.pipeline.orchestrator import Orchestrator, get_orchestrator

        # Publishing
        from src.publishing.rewriter import ContentRewriter
        from src.publishing.scheduler import PublishingScheduler

        # Storage
        from src.storage.db import StorageFacade, get_storage
        from src.storage.sqlite_adapter import SQLiteAdapter
        from src.utils.duplicate_detector import DuplicateDetector
        from src.utils.logging_config import get_logger

        # Utilities
        from src.utils.post_validator import validate_post

        result.passed = True
        result.details = {"imported_modules": 15}

    except ImportError as e:
        result.error = str(e)
        result.passed = False

    return result


def test_environment() -> TestResult:
    """Test environment configuration"""
    result = TestResult("Environment")

    try:
        from dotenv import load_dotenv

        load_dotenv()

        # Check critical environment variables
        required_vars = [
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ]

        optional_vars = [
            "SUPABASE_SERVICE_ROLE_KEY",
            "MISTRAL_API_KEY",
            "GEMINI_API_KEY",
            "OLLAMA_URL",
            "TELEGRAM_BOT_TOKEN",
            "REDDIT_CLIENT_ID",
            "REDDIT_CLIENT_SECRET",
            "TWITTER_USERNAME",
            "TWITTER_PASSWORD",
        ]

        missing_required = []
        missing_optional = []

        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)

        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)

        if missing_required:
            result.error = f"Missing required vars: {', '.join(missing_required)}"
            result.passed = False
        else:
            result.passed = True
            if missing_optional:
                result.warnings.append(
                    f"Missing optional vars: {', '.join(missing_optional)}"
                )

        result.details = {
            "required_vars": len(required_vars) - len(missing_required),
            "optional_vars": len(optional_vars) - len(missing_optional),
            "missing_optional": missing_optional,
        }

    except Exception as e:
        result.error = str(e)
        result.passed = False

    return result


# ============================================================================
# TEST 2: DATABASE CONNECTIVITY
# ============================================================================


def test_database_connectivity() -> TestResult:
    """Test database connections"""
    result = TestResult("Database Connectivity")

    try:
        from src.database.database_agent import DatabaseAgent

        db = DatabaseAgent()

        # Test SQLite
        sqlite_ok = db._sqlite is not None
        if sqlite_ok:
            try:
                # Try a simple query
                cur = db._sqlite.conn.cursor()
                cur.execute("SELECT COUNT(*) FROM posts LIMIT 1")
                cur.fetchone()
                sqlite_test = True
            except Exception as e:
                sqlite_test = False
                result.warnings.append(f"SQLite query failed: {e}")
        else:
            sqlite_test = False
            result.warnings.append("SQLite not available")

        # Test Supabase
        supabase_ok = db._supabase is not None
        if supabase_ok:
            try:
                # Try a simple query
                response = db._supabase.table("posts").select("id").limit(1).execute()
                supabase_test = True
            except Exception as e:
                supabase_test = False
                result.warnings.append(f"Supabase query failed: {e}")
        else:
            supabase_test = False
            result.warnings.append("Supabase not available")

        if not sqlite_ok and not supabase_ok:
            result.error = "No database connections available"
            result.passed = False
        elif not sqlite_test and not supabase_test:
            result.error = "Database connections exist but queries fail"
            result.passed = False
        else:
            result.passed = True

        result.details = {
            "sqlite_available": sqlite_ok,
            "sqlite_test": sqlite_test,
            "supabase_available": supabase_ok,
            "supabase_test": supabase_test,
        }

    except Exception as e:
        result.error = str(e)
        result.passed = False
        result.details = {"traceback": traceback.format_exc()}

    return result


def test_database_operations() -> TestResult:
    """Test basic database operations"""
    result = TestResult("Database Operations")

    try:
        from src.database.database_agent import DatabaseAgent
        from src.storage.sqlite_adapter import SQLiteAdapter

        db = DatabaseAgent()

        # Test count_incomplete_posts
        try:
            incomplete_count = db.count_incomplete_posts()
            count_works = True
        except Exception as e:
            count_works = False
            result.warnings.append(f"count_incomplete_posts failed: {e}")
            incomplete_count = 0

        # Test SQLiteAdapter for getting posts
        try:
            sqlite = SQLiteAdapter()
            # Try to get a count from SQLite
            cur = sqlite.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM posts")
            post_count = cur.fetchone()[0]
            sqlite_works = True
        except Exception as e:
            sqlite_works = False
            post_count = 0
            result.warnings.append(f"SQLite query failed: {e}")

        # Test get_last_post_id
        try:
            last_id = db.get_last_post_id("twitter")
            get_last_id_works = True
        except Exception as e:
            get_last_id_works = False
            last_id = None
            result.warnings.append(f"get_last_post_id failed: {e}")

        if count_works or sqlite_works or get_last_id_works:
            result.passed = True
        else:
            result.error = "All database operations failed"
            result.passed = False

        result.details = {
            "count_incomplete_posts": count_works,
            "sqlite_query": sqlite_works,
            "get_last_post_id": get_last_id_works,
            "post_count": post_count,
            "incomplete_count": incomplete_count,
        }

    except Exception as e:
        result.error = str(e)
        result.passed = False
        result.details = {"traceback": traceback.format_exc()}

    return result


# ============================================================================
# TEST 3: COLLECTION WORKFLOWS
# ============================================================================


async def test_collection_orchestrator() -> TestResult:
    """Test collection orchestrator"""
    result = TestResult("Collection Orchestrator")

    try:
        from src.pipeline.orchestrator import get_orchestrator

        orch = get_orchestrator()

        # Test orchestrator initialization
        if orch is None:
            result.error = "Orchestrator is None"
            result.passed = False
            return result

        result.passed = True
        result.details = {"orchestrator_initialized": True}

    except Exception as e:
        result.error = str(e)
        result.passed = False
        result.details = {"traceback": traceback.format_exc()}

    return result


async def test_collectors_initialization() -> TestResult:
    """Test that collectors can be initialized"""
    result = TestResult("Collectors Initialization")

    collectors = {}
    errors = {}

    # Test Twitter extractor
    try:
        from src.core.extraction.twitter_extractor_playwright import (
            TwitterExtractorPlaywright,
        )

        username = os.getenv("TWITTER_USERNAME")
        if username:
            extractor = TwitterExtractorPlaywright(username=username)
            collectors["twitter"] = True
        else:
            collectors["twitter"] = False
            errors["twitter"] = "TWITTER_USERNAME not set"
    except Exception as e:
        collectors["twitter"] = False
        errors["twitter"] = str(e)

    # Test Reddit extractor
    try:
        from src.core.extraction.reddit_extractor import RedditExtractor

        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        if client_id and client_secret:
            extractor = RedditExtractor(
                client_id=client_id,
                client_secret=client_secret,
                user_agent="BEYONDLINES/1.0",
            )
            collectors["reddit"] = True
        else:
            collectors["reddit"] = False
            errors["reddit"] = "REDDIT credentials not set"
    except Exception as e:
        collectors["reddit"] = False
        errors["reddit"] = str(e)

    # Test Threads extractor
    try:
        from src.core.extraction.threads_extractor import ThreadsExtractor

        extractor = ThreadsExtractor()
        collectors["threads"] = True
    except Exception as e:
        collectors["threads"] = False
        errors["threads"] = str(e)

    if all(collectors.values()):
        result.passed = True
    elif any(collectors.values()):
        result.passed = True
        result.warnings = [
            f"{k}: {v}" for k, v in errors.items() if not collectors.get(k)
        ]
    else:
        result.error = "All collectors failed to initialize"
        result.passed = False

    result.details = {"collectors": collectors, "errors": errors}

    return result


# ============================================================================
# TEST 4: ANALYSIS WORKFLOW
# ============================================================================


async def test_analyzer_initialization() -> TestResult:
    """Test analyzer initialization"""
    result = TestResult("Analyzer Initialization")

    try:
        from src.core.analysis.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()

        # Check which services are available
        services = {
            "ollama": analyzer._ollama_client is not None
            if hasattr(analyzer, "_ollama_client")
            else False,
            "mistral": analyzer._mistral_client is not None
            if hasattr(analyzer, "_mistral_client")
            else False,
            "gemini": analyzer.gemini_model is not None
            if hasattr(analyzer, "gemini_model")
            else False,
        }

        # Check ai_services list
        if hasattr(analyzer, "ai_services") and analyzer.ai_services:
            available_services = [
                s.get("name") for s in analyzer.ai_services if s.get("name")
            ]
        else:
            available_services = [k for k, v in services.items() if v]

        if not any(services.values()) and not available_services:
            result.error = "No AI services available"
            result.passed = False
        else:
            result.passed = True
            if len(available_services) < 3:
                result.warnings.append(
                    f"Only {len(available_services)}/3 AI services available: {available_services}"
                )

        result.details = {"services": services, "available": available_services}

    except Exception as e:
        result.error = str(e)
        result.passed = False
        result.details = {"traceback": traceback.format_exc()}

    return result


# ============================================================================
# TEST 5: PUBLISHING WORKFLOW
# ============================================================================


def test_rewriter_initialization() -> TestResult:
    """Test rewriter initialization"""
    result = TestResult("Rewriter Initialization")

    try:
        from src.publishing.rewriter import ContentRewriter

        rewriter = ContentRewriter()

        # Check if Ollama is available (required for rewriting)
        ollama_available = False
        try:
            import httpx

            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
            response = httpx.get(f"{ollama_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                ollama_available = True
        except Exception:
            pass

        if not ollama_available:
            result.error = "Ollama not available (rewriter requires Ollama)"
            result.passed = False
            result.warnings.append("Rewriter has no fallback - single point of failure")
        else:
            result.passed = True

        result.details = {"ollama_available": ollama_available}

    except Exception as e:
        result.error = str(e)
        result.passed = False
        result.details = {"traceback": traceback.format_exc()}

    return result


def test_scheduler_initialization() -> TestResult:
    """Test scheduler initialization"""
    result = TestResult("Scheduler Initialization")

    try:
        from src.publishing.scheduler import PublishingScheduler

        scheduler = PublishingScheduler()
        result.passed = True
        result.details = {"scheduler_initialized": True}

    except Exception as e:
        result.error = str(e)
        result.passed = False
        result.details = {"traceback": traceback.format_exc()}

    return result


# ============================================================================
# TEST 6: UTILITIES
# ============================================================================


def test_post_validator() -> TestResult:
    """Test post validator"""
    result = TestResult("Post Validator")

    try:
        from src.utils.post_validator import validate_post

        # Test with valid post
        valid_post = {
            "post_id": "test_123",
            "platform": "twitter",
            "content": "This is a test post with enough content to pass validation.",
            "author": "test_user",
            "url": "https://twitter.com/test/status/123",
            "created_at": datetime.now().isoformat(),
        }

        validation_result = validate_post(valid_post)

        # validate_post returns a ValidationResult object
        is_valid = validation_result.is_valid
        errors = validation_result.errors

        if is_valid:
            result.passed = True
        else:
            result.error = f"Valid post failed validation: {errors}"
            result.passed = False

        result.details = {
            "validation_works": is_valid,
            "errors": errors,
            "warnings": validation_result.warnings,
        }

    except Exception as e:
        result.error = str(e)
        result.passed = False
        result.details = {"traceback": traceback.format_exc()}

    return result


def test_duplicate_detector() -> TestResult:
    """Test duplicate detector"""
    result = TestResult("Duplicate Detector")

    try:
        from src.database.manager import SupabaseManager
        from src.utils.duplicate_detector import DuplicateDetector

        supabase_manager = SupabaseManager() if os.getenv("SUPABASE_URL") else None
        detector = DuplicateDetector(db_manager=None, supabase_manager=supabase_manager)

        result.passed = True
        result.details = {"detector_initialized": True}

    except Exception as e:
        result.error = str(e)
        result.passed = False
        result.details = {"traceback": traceback.format_exc()}

    return result


# ============================================================================
# MAIN VALIDATION RUNNER
# ============================================================================


async def run_all_tests() -> Dict[str, Any]:
    """Run all validation tests"""
    results = []

    print_header("MECHANICAL PARTS VALIDATION")

    # Test 1: Environment & Imports
    print_header("1. Environment & Imports")
    results.append(test_imports())
    results.append(test_environment())

    # Test 2: Database
    print_header("2. Database Operations")
    results.append(test_database_connectivity())
    results.append(test_database_operations())

    # Test 3: Collection
    print_header("3. Collection Workflows")
    results.append(await test_collection_orchestrator())
    results.append(await test_collectors_initialization())

    # Test 4: Analysis
    print_header("4. Analysis Workflow")
    results.append(await test_analyzer_initialization())

    # Test 5: Publishing
    print_header("5. Publishing Workflow")
    results.append(test_rewriter_initialization())
    results.append(test_scheduler_initialization())

    # Test 6: Utilities
    print_header("6. Utilities")
    results.append(test_post_validator())
    results.append(test_duplicate_detector())

    # Summary
    print_header("VALIDATION SUMMARY")

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    warnings_count = sum(len(r.warnings) for r in results)

    print(f"\n{BOLD}Results:{RESET}")
    print(f"  {GREEN}✅ Passed: {passed}/{len(results)}{RESET}")
    print(f"  {RED}❌ Failed: {failed}/{len(results)}{RESET}")
    print(f"  {YELLOW}⚠️  Warnings: {warnings_count}{RESET}")

    print(f"\n{BOLD}Test Details:{RESET}")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print_test(result.name, status, result.error, result.details)
        if result.warnings:
            for warning in result.warnings:
                print(f"   {YELLOW}⚠️  {warning}{RESET}")

    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "warnings": warnings_count,
        "results": results,
    }


if __name__ == "__main__":
    try:
        results = asyncio.run(run_all_tests())
        sys.exit(0 if results["failed"] == 0 else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Validation interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Validation failed with error: {e}{RESET}")
        traceback.print_exc()
        sys.exit(1)
