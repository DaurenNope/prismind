#!/usr/bin/env python3
"""
Process backlog without new collection:
- Analyze existing pool (optional via flags)
- Rewrite for specified profiles
- Auto-schedule if enabled (delay controlled by flags)
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.automation.auto_pipeline import AutoPipeline


async def main() -> int:
    profiles = ["cryptoniard", "qronoya"]
    pipeline = AutoPipeline()

    print("⚙️  Processing backlog (no new collection)...")
    summary = await pipeline.process_backlog_for_profiles(
        profiles=profiles, posts_per_profile=None
    )

    print("=== Backlog Summary ===")
    for k, v in (summary or {}).items():
        print(f"- {k}: {v}")

    # Return nonzero if nothing happened to make it obvious
    did_anything = bool(summary.get("rewritten") or summary.get("analyzed"))
    return 0 if did_anything else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


