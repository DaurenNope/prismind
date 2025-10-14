#!/usr/bin/env python3
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    if logging.getLogger().handlers:
        return
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


