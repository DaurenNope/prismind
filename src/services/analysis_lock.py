#!/usr/bin/env python3
"""File-based lock to prevent concurrent analysis runs."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

LOCK_DIR = Path("var")
LOCK_DIR.mkdir(parents=True, exist_ok=True)


def _lock_path(name: str = "analysis") -> Path:
    return LOCK_DIR / f"{name}.lock"


def acquire_analysis_lock(name: str = "analysis") -> bool:
    """Attempt to acquire the named analysis lock.

    Returns True when the lock is acquired, False if it is already held.
    """

    path = _lock_path(name)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        logger.error(f"Error: {e}")
        return False

    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(str(os.getpid()))
    except Exception as e:
        logger.error(f"Error: {e}")
        # Best effort cleanup if we fail to write
        try:
            path.unlink()
        except FileNotFoundError:
            logger.error(f"Error: {e}")
            pass
        return False

    return True


def release_analysis_lock(name: str = "analysis") -> None:
    """Release the named analysis lock if held."""

    path = _lock_path(name)
    try:
        path.unlink()
    except FileNotFoundError:
        logger.error(f"Error: {e}")
        pass


@contextmanager
def analysis_lock_guard(name: str = "analysis") -> Iterator[bool]:
    """Context manager that acquires the analysis lock for the duration.

    Yields True if the lock was acquired, False otherwise (and exits immediately).
    """

    acquired = acquire_analysis_lock(name)
    try:
        yield acquired
    finally:
        if acquired:
            release_analysis_lock(name)
