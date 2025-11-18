#!/usr/bin/env python3
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path("var")
BASE_DIR.mkdir(parents=True, exist_ok=True)


def _flag_path(name: str) -> Path:
    return BASE_DIR / f"cancel_{name}.flag"


def request_cancel(name: str = "all") -> None:
    _flag_path(name).write_text("1")


def clear_cancel(name: str = "all") -> None:
    try:
        _flag_path(name).unlink()
    except FileNotFoundError:
        logger.error(f"Error: {e}")
        pass


def is_cancelled(name: str = "all") -> bool:
    return _flag_path(name).exists()
