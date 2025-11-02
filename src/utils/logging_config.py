#!/usr/bin/env python3
"""
Centralized logging configuration for PrisMind.
Provides consistent logging across all modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class PrisMindLogger:
    """Centralized logger for PrisMind application"""

    _initialized = False
    _log_dir = Path("logs")

    @classmethod
    def setup(cls, level: int = logging.INFO, log_to_file: bool = True) -> None:
        """
        Setup logging configuration for the entire application.

        Args:
            level: Logging level (default: INFO)
            log_to_file: Whether to log to file (default: True)
        """
        if cls._initialized:
            return

        # Create logs directory if logging to file
        if log_to_file:
            cls._log_dir.mkdir(exist_ok=True)

        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        simple_formatter = logging.Formatter(
            fmt='%(levelname)s - %(message)s'
        )

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)

        # File handler (DEBUG and above) - if enabled
        if log_to_file:
            log_file = cls._log_dir / f"prismind_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(file_handler)

        # Set specific loggers to reduce noise
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('playwright').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)

        cls._initialized = True
        logging.info("Logging system initialized")

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance for a specific module.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Logger instance
        """
        if not cls._initialized:
            cls.setup()

        return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return PrisMindLogger.get_logger(name)


# Auto-initialize on import with default settings
PrisMindLogger.setup()
