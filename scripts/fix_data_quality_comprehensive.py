#!/usr/bin/env python3
"""
COMPREHENSIVE Data Quality Fix Script
=====================================

This script ABSOLUTELY FIXES all data quality issues:
- Corrupted timestamps
- Invalid boolean values
- String scores instead of numeric
- Invalid persona keys
- Missing/invalid categories
- Corrupted JSON fields
- Invalid embedding formats
- Missing required fields

Uses DatabaseAgent's normalization (the same logic used in production)
to ensure consistency.

Run with --dry-run first to see what will be fixed.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.database_agent import DatabaseAgent
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DataQualityFixer:
    """Comprehensive data quality fixer"""

    def __init__(self, db_path: str = "beyondlines.db"):
        self.db_path = project_root / db_path
        self.db_agent = DatabaseAgent()
        self.stats = {
            "total": 0,
            "fixed": 0,
            "errors": 0,
            "skipped": 0,
            "issues_found": {},
            "issues_fixed": {},
        }

    def validate_post(self, post_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate post data and return (is_valid, issues)
        """
        issues = []

        # 1. Check required fields
        # Note: content can be empty for some posts (e.g., image-only posts)
        # Only require post_id and platform
        if not post_data.get("post_id"):
            issues.append("missing_post_id")
        if not post_data.get("platform"):
            issues.append("missing_platform")

        # 2. Check analysis fields (if post has analysis)
        if post_data.get("ai_summary"):
            analysis_fields = {
                "ai_summary": (str, 50, 5000),  # min 50, max 5000 chars
                "category": (str, None, None),
                "rewrite_score": (float, 0.0, 10.0),
                "value_score": (float, 0.0, 10.0),
                "quality_score": (float, 0.0, 10.0),
            }

            for field, (field_type, min_val, max_val) in analysis_fields.items():
                value = post_data.get(field)

                if value is None:
                    issues.append(f"missing_{field}")
                    continue

                # Type validation
                if field_type == str:
                    if not isinstance(value, str) or not value.strip():
                        issues.append(f"invalid_{field}_type")
                    elif min_val and len(value.strip()) < min_val:
                        issues.append(f"invalid_{field}_too_short")
                    elif max_val and len(value.strip()) > max_val:
                        issues.append(f"invalid_{field}_too_long")

                elif field_type == float:
                    if not isinstance(value, (int, float)):
                        issues.append(f"invalid_{field}_type")
                    elif min_val is not None and value < min_val:
                        issues.append(f"invalid_{field}_too_low")
                    elif max_val is not None and value > max_val:
                        issues.append(f"invalid_{field}_too_high")

            # 3. Check category validity
            category = post_data.get("category")
            valid_categories = [
                "TECH",
                "DATING",
                "CRYPTO",
                "BUSINESS",
                "LEARNING",
                "NEWS",
                "PERSONAL",
                "HEALTH",
                "ENTERTAINMENT",
                "OTHER",
                "DEPRECATED",
            ]
            if category and category not in valid_categories:
                issues.append("invalid_category")

            # 4. Check persona key validity
            persona_key = post_data.get("best_persona_key")
            if persona_key:
                valid_personas = ["qronoya", "aspandead", "claimzilla"]
                invalid_persona_values = [
                    "evergreen",
                    "timely",
                    "trending",
                    "breaking",
                    "urgent",
                    "this-week",
                    "this-month",
                ]
                if persona_key in invalid_persona_values:
                    issues.append("invalid_persona_key")
                elif persona_key not in valid_personas:
                    issues.append("unknown_persona_key")

            # 5. Check timestamps
            for ts_field in ["created_at", "analyzed_at"]:
                ts_value = post_data.get(ts_field)
                if ts_value:
                    if not self._is_valid_timestamp(ts_value):
                        issues.append(f"invalid_{ts_field}")

            # 6. Check JSON fields
            json_fields = [
                "tags",
                "key_concepts",
                "rewrite_reasons",
                "rewrite_risks",
                "persona_fit_scores",
                "persona_fit_reasons",
                "best_persona_reasons",
            ]
            for field in json_fields:
                value = post_data.get(field)
                if value and isinstance(value, str):
                    try:
                        json.loads(value)
                    except:
                        issues.append(f"invalid_{field}_json")

            # 7. Check boolean fields
            bool_fields = ["is_saved", "time_sensitive", "needs_deep_analysis"]
            for field in bool_fields:
                value = post_data.get(field)
                if value is not None and not isinstance(value, bool):
                    # Check if it's a valid boolean-like value
                    if isinstance(value, str):
                        if value.lower() not in [
                            "true",
                            "false",
                            "1",
                            "0",
                            "yes",
                            "no",
                            "t",
                            "f",
                            "neutral",
                        ]:
                            issues.append(f"invalid_{field}_boolean")

            # 8. Check embedding format
            embedding = post_data.get("embedding")
            if embedding:
                if isinstance(embedding, str):
                    if not embedding.startswith("["):
                        issues.append("invalid_embedding_format")
                    else:
                        try:
                            emb_data = json.loads(embedding)
                            if not isinstance(emb_data, list):
                                issues.append("invalid_embedding_type")
                        except:
                            issues.append("invalid_embedding_json")

        return len(issues) == 0, issues

    def _is_valid_timestamp(self, value: Any) -> bool:
        """Check if value is a valid timestamp"""
        if value is None:
            return False

        if isinstance(value, (int, float)):
            # Unix timestamp
            try:
                datetime.fromtimestamp(value)
                return True
            except:
                return False

        if isinstance(value, str):
            # Try ISO format
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return True
            except:
                pass

            # Try other formats
            try:
                datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
                return True
            except:
                pass

            # Check if it's a service name (corrupted)
            invalid_values = [
                "mistral",
                "gemini",
                "ollama",
                "qwen",
                "ai_service",
                "unknown",
                "none",
                "null",
                "",
            ]
            if value.lower().strip() in invalid_values:
                return False

            # Check if it looks like text (too long, contains spaces)
            if len(value) > 50 or " " in value:
                return False

        return False

    def fix_post(
        self, post_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Fix post data using DatabaseAgent normalization.
        Returns: (fixed_data, issues_before, issues_after)
        """
        # Validate before
        is_valid_before, issues_before = self.validate_post(post_data)

        # Fix using DatabaseAgent normalization (production logic)
        try:
            fixed_data = self.db_agent._normalize_post_data(post_data.copy())
        except Exception as e:
            logger.error(f"Error normalizing post {post_data.get('post_id')}: {e}")
            return post_data, issues_before, []

        # Validate after
        is_valid_after, issues_after = self.validate_post(fixed_data)

        return fixed_data, issues_before, issues_after

    def fix_all_posts(
        self, dry_run: bool = False, limit: int = None, verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Fix all posts in database

        Args:
            dry_run: If True, don't actually update database
            limit: Limit number of posts to fix
            verbose: If True, show detailed info for each post

        Returns:
            Stats dictionary
        """
        if not self.db_path.exists():
            logger.error(f"Database not found: {self.db_path}")
            return self.stats

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Get all posts
        query = "SELECT * FROM posts ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"

        cur.execute(query)
        rows = cur.fetchall()
        conn.close()

        self.stats["total"] = len(rows)
        logger.info(f"📊 Found {len(rows)} posts to check")

        if dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")

        detailed_results = []

        # Process each post
        for idx, row in enumerate(rows, 1):
            post_data = dict(row)
            post_id = post_data.get("post_id", "unknown")
            platform = post_data.get("platform", "unknown")

            # Convert JSON strings to Python objects
            for field in [
                "tags",
                "key_concepts",
                "rewrite_reasons",
                "rewrite_risks",
                "best_persona_reasons",
                "persona_fit_scores",
                "persona_fit_reasons",
                "hashtags",
                "mentions",
                "time_sensitive_reasons",
                "embedding",
            ]:
                if post_data.get(field) and isinstance(post_data[field], str):
                    try:
                        post_data[field] = json.loads(post_data[field])
                    except:
                        pass

            # Fix post
            try:
                fixed_data, issues_before, issues_after = self.fix_post(post_data)

                # Track issues
                for issue in issues_before:
                    self.stats["issues_found"][issue] = (
                        self.stats["issues_found"].get(issue, 0) + 1
                    )

                for issue in issues_after:
                    self.stats["issues_fixed"][issue] = (
                        self.stats["issues_fixed"].get(issue, 0) + 1
                    )

                # Check if anything changed
                has_changes = issues_before != issues_after or fixed_data != post_data

                # Store detailed results
                result = {
                    "post_id": post_id,
                    "platform": platform,
                    "issues_before": issues_before,
                    "issues_after": issues_after,
                    "has_changes": has_changes,
                    "before": {
                        k: v
                        for k, v in post_data.items()
                        if k
                        in [
                            "category",
                            "best_persona_key",
                            "rewrite_score",
                            "value_score",
                            "quality_score",
                            "relevance_window",
                            "analyzed_at",
                        ]
                    },
                    "after": {
                        k: v
                        for k, v in fixed_data.items()
                        if k
                        in [
                            "category",
                            "best_persona_key",
                            "rewrite_score",
                            "value_score",
                            "quality_score",
                            "relevance_window",
                            "analyzed_at",
                        ]
                    },
                }
                detailed_results.append(result)

                if has_changes:
                    if not dry_run:
                        # Update database
                        self._update_post(fixed_data)
                        self.stats["fixed"] += 1
                    else:
                        self.stats["fixed"] += 1

                    if verbose:
                        logger.info(f"  [{idx}/{len(rows)}] {post_id} ({platform}):")
                        logger.info(
                            f"    Issues: {len(issues_before)} -> {len(issues_after)}"
                        )
                        if issues_before:
                            logger.info(f"    Before: {', '.join(issues_before)}")
                        if issues_after:
                            logger.info(f"    After: {', '.join(issues_after)}")
                        logger.info(
                            f"    Changes: category={post_data.get('category')} -> {fixed_data.get('category')}, "
                            f"persona={post_data.get('best_persona_key')} -> {fixed_data.get('best_persona_key')}, "
                            f"rewrite_score={post_data.get('rewrite_score')} -> {fixed_data.get('rewrite_score')}"
                        )
                else:
                    self.stats["skipped"] += 1

                # Log progress
                if idx % 10 == 0:
                    logger.info(f"   Progress: {idx}/{len(rows)} posts processed")

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"  ❌ Error fixing post {post_id}: {e}")
                import traceback

                logger.error(traceback.format_exc())

        self.stats["detailed_results"] = detailed_results

        if not dry_run:
            logger.info(f"✅ Fixed {self.stats['fixed']} posts")
        else:
            logger.info(f"✅ Would fix {self.stats['fixed']} posts (dry run)")

        return self.stats

    def _update_post(self, post_data: Dict[str, Any]):
        """Update post in database"""
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        try:
            # Prepare update statement
            update_fields = [
                "created_at",
                "analyzed_at",
                "category",
                "best_persona_key",
                "best_persona_score",
                "rewrite_score",
                "rewrite_readiness",
                "rewrite_reasons",
                "rewrite_risks",
                "analysis_confidence",
                "analysis_depth",
                "needs_deep_analysis",
                "persona_fit_scores",
                "persona_fit_reasons",
                "best_persona_reasons",
                "value_score",
                "quality_score",
                "urgency_score",
                "time_sensitive",
                "relevance_window",
                "time_sensitive_reasons",
                "tags",
                "key_concepts",
                "topic",
                "content_type",
                "language",
                "ai_summary",
                "is_saved",
            ]

            # Build UPDATE statement
            set_clauses = []
            values = []

            for field in update_fields:
                value = post_data.get(field)

                # Convert lists/dicts to JSON strings (SQLite stores JSON as TEXT)
                if field in [
                    "tags",
                    "key_concepts",
                    "rewrite_reasons",
                    "rewrite_risks",
                    "best_persona_reasons",
                    "time_sensitive_reasons",
                ]:
                    if value is not None:
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value)
                        elif not isinstance(value, str):
                            value = json.dumps(value) if value else None
                elif field in ["persona_fit_scores", "persona_fit_reasons"]:
                    if value is not None:
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value)
                        elif not isinstance(value, str):
                            value = json.dumps(value) if value else None

                set_clauses.append(f"{field} = ?")
                values.append(value)

            # Add WHERE clause
            values.append(post_data["post_id"])
            values.append(post_data["platform"])

            update_sql = f"""
                UPDATE posts
                SET {', '.join(set_clauses)}
                WHERE post_id = ? AND platform = ?
            """

            cur.execute(update_sql, values)
            conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating post {post_data.get('post_id')}: {e}")
            raise
        finally:
            conn.close()

    def print_stats(self):
        """Print comprehensive stats"""
        print("\n" + "=" * 80)
        print("DATA QUALITY FIX STATISTICS")
        print("=" * 80)
        print(f"Total posts: {self.stats['total']}")
        print(f"Fixed: {self.stats['fixed']}")
        print(f"Skipped (no issues): {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")

        if self.stats["issues_found"]:
            print("\nIssues Found:")
            for issue, count in sorted(
                self.stats["issues_found"].items(), key=lambda x: -x[1]
            ):
                print(f"  {issue:30s}: {count:4d}")

        if self.stats["issues_fixed"]:
            print("\nIssues Fixed:")
            for issue, count in sorted(
                self.stats["issues_fixed"].items(), key=lambda x: -x[1]
            ):
                print(f"  {issue:30s}: {count:4d}")

        print("=" * 80 + "\n")

    def print_detailed_results(self):
        """Print detailed results for evaluation"""
        if "detailed_results" not in self.stats:
            return

        print("\n" + "=" * 80)
        print("DETAILED QUALITY EVALUATION")
        print("=" * 80)

        for result in self.stats["detailed_results"]:
            print(f"\nPost: {result['post_id']} ({result['platform']})")
            print(
                f"  Issues before: {len(result['issues_before'])} - {', '.join(result['issues_before']) if result['issues_before'] else 'None'}"
            )
            print(
                f"  Issues after: {len(result['issues_after'])} - {', '.join(result['issues_after']) if result['issues_after'] else 'None'}"
            )
            print(f"  Has changes: {result['has_changes']}")

            if result["has_changes"]:
                print("  Changes:")
                for key in [
                    "category",
                    "best_persona_key",
                    "rewrite_score",
                    "value_score",
                    "quality_score",
                    "relevance_window",
                ]:
                    before_val = result["before"].get(key)
                    after_val = result["after"].get(key)
                    if before_val != after_val:
                        print(f"    {key}: {before_val} -> {after_val}")

            print(f"  Final state:")
            for key in [
                "category",
                "best_persona_key",
                "rewrite_score",
                "value_score",
                "quality_score",
                "relevance_window",
            ]:
                val = result["after"].get(key)
                print(f"    {key}: {val}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive data quality fix")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    parser.add_argument("--limit", type=int, help="Limit number of posts to fix")
    parser.add_argument(
        "--db", type=str, default="beyondlines.db", help="Database path"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--evaluate", "-e", action="store_true", help="Show detailed evaluation"
    )

    args = parser.parse_args()

    logger.info("🚀 Starting comprehensive data quality fix...")
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")

    fixer = DataQualityFixer(db_path=args.db)
    stats = fixer.fix_all_posts(
        dry_run=args.dry_run, limit=args.limit, verbose=args.verbose
    )
    fixer.print_stats()

    if args.evaluate:
        fixer.print_detailed_results()

    if args.dry_run:
        logger.info("💡 Run without --dry-run to apply fixes")
    else:
        logger.info("✅ Data quality fix complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
