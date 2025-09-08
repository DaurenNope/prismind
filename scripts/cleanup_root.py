#!/usr/bin/env python3
"""
Root cleanup utility: organizes top-level files into clearer locations.

Moves (idempotent):
- Documentation *.md into docs/
- App entry points into apps/

Run:
  python scripts/cleanup_root.py --apply

Pass --dry-run to preview.
"""

import argparse
import os
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DOC_TARGET = REPO / "docs"
APP_TARGET = REPO / "apps"

DOC_FILES = [
    "BACKEND_ARCHITECTURE.md",
    "DESIGN.md",
    "EVOLUTION_PLAN.md",
    "PROFESSIONAL_REFACTOR_PLAN.md",
    "PROGRESS.md",
    "SAFE_REFACTOR_STRATEGY.md",
    "FREE_DEPLOYMENT_GUIDE.md",
    "DEPLOYMENT_GUIDE.md",
    "QUICK_DEPLOY.md",
    "START_GUIDE.md",
    "USE_CASES.md",
    "ROADMAP.md",
]

APP_FILES = [
    "demo_app.py",
    "streamlit_app.py",
]


def move_file(src: Path, dst_dir: Path, dry_run: bool) -> bool:
    if not src.exists():
        return False
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        # Already moved/copy present; remove source if same content?
        return False
    print(f"MOVE {src.relative_to(REPO)} -> {dst.relative_to(REPO)}")
    if not dry_run:
        shutil.move(str(src), str(dst))
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Perform changes")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    dry_run = not args.apply or args.dry_run

    moved = 0
    # Documentation
    for name in DOC_FILES:
        moved |= move_file(REPO / name, DOC_TARGET, dry_run)
    # Apps
    for name in APP_FILES:
        moved |= move_file(REPO / name, APP_TARGET, dry_run)

    print("Done.")


if __name__ == "__main__":
    main()


