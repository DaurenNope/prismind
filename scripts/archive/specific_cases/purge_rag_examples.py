#!/usr/bin/env python3
"""
Utility to purge low-quality persona examples from the RAG store.

Usage:
    python scripts/purge_rag_examples.py --min-quality 80 --allow-invalid
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.domain.publishing.rag_system import ExampleVectorDatabase  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purge low-quality RAG examples")
    parser.add_argument(
        "--min-quality",
        type=float,
        default=78.0,
        help="Minimum acceptable quality score (default: 78)",
    )
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="Keep examples even if fact/voice validators failed",
    )
    parser.add_argument(
        "--storage-path",
        type=str,
        default="data/vector_db",
        help="Path to the vector DB storage directory",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    db = ExampleVectorDatabase(storage_path=args.storage_path)
    removed = db.purge_low_quality(
        min_quality=args.min_quality,
        require_validators=not args.allow_invalid,
    )
    print(f"Purged {removed} examples below {args.min_quality} quality threshold")


if __name__ == "__main__":
    main()

