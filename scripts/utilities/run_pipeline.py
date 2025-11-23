#!/usr/bin/env python3
"""
Unified automation runner that executes collection → analysis → curation → rewrite.

Scheduling/posting remains manual unless --auto-schedule is provided.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.application.automation.full_automation_loop import FullAutomationLoop
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


async def run_pipeline(args) -> None:
    orchestrator = FullAutomationLoop()
    summary = {
        "collection": None,
        "analysis": None,
        "curation": None,
        "transformation": None,
    }

    if not args.skip_collection:
        summary["collection"] = await orchestrator.run_collection(
            platforms=args.platforms
        )
    else:
        logger.info("⏭️ Skipping collection phase")

    if not args.skip_analysis:
        summary["analysis"] = await orchestrator.run_analysis(
            limit=args.analyze_limit
        )
    else:
        logger.info("⏭️ Skipping analysis phase")

    if not args.skip_curation:
        summary["curation"] = orchestrator.run_curation_backfill(
            batch_size=args.curation_batch_size, max_batches=args.curation_batches
        )
    else:
        logger.info("⏭️ Skipping curation backfill")

    if not args.skip_rewrites:
        summary["transformation"] = await orchestrator.run_transformation_and_scheduling(
            min_match_score=args.min_match_score,
            schedule_minutes=args.schedule_minutes,
            auto_schedule=args.auto_schedule,
        )
    else:
        logger.info("⏭️ Skipping rewrite generation")

    logger.info("\n================ PIPELINE SUMMARY ================")
    for key, value in summary.items():
        logger.info(f"{key.title()}: {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run automated pipeline up through rewrite generation."
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        help="Limit collection to specific platforms (twitter, threads, reddit)",
    )
    parser.add_argument(
        "--analyze-limit",
        type=int,
        help="Maximum posts to analyze this run (default: all unanalyzed)",
    )
    parser.add_argument(
        "--min-match-score",
        type=float,
        default=0.65,
        help="Minimum persona match score for rewrites",
    )
    parser.add_argument(
        "--schedule-minutes",
        type=int,
        default=60,
        help="Minutes in the future for auto-scheduled posts (if enabled)",
    )
    parser.add_argument(
        "--auto-schedule",
        action="store_true",
        help="Also insert rewrites into scheduled_posts (default: disabled)",
    )
    parser.add_argument(
        "--curation-batch-size",
        type=int,
        default=500,
        help="Number of posts per curation batch (default: 500)",
    )
    parser.add_argument(
        "--curation-batches",
        type=int,
        default=2,
        help="How many curation batches to run after analysis (default: 2)",
    )

    parser.add_argument("--skip-collection", action="store_true")
    parser.add_argument("--skip-analysis", action="store_true")
    parser.add_argument("--skip-curation", action="store_true")
    parser.add_argument("--skip-rewrites", action="store_true")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()

