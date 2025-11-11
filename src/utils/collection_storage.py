#!/usr/bin/env python3
"""
Persistent storage helpers for collection history and logs.

Stores lightweight JSON files inside the local `var/` directory so that the
Streamlit UI can display collection results from previous sessions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class CollectionStorage:
    def __init__(
        self,
        history_path: Path = Path("var/collection_history.json"),
        logs_path: Path = Path("var/collection_logs.json"),
    ) -> None:
        self.history_path = history_path
        self.logs_path = logs_path
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.logs_path.parent.mkdir(parents=True, exist_ok=True)

    # ----------------------------
    # Generic helpers
    # ----------------------------
    @staticmethod
    def _safe_load(path: Path) -> List[Dict]:
        if not path.exists():
            return []
        try:
            with path.open("r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.warning("Failed to load %s: %s", path, exc)
        return []

    @staticmethod
    def _safe_write(path: Path, records: Iterable[Dict]) -> None:
        try:
            with path.open("w") as f:
                json.dump(list(records), f, indent=2)
        except Exception as exc:
            logger.warning("Failed to write %s: %s", path, exc)

    # ----------------------------
    # History
    # ----------------------------
    def load_history(self, limit: int = 200) -> List[Dict]:
        records = self._safe_load(self.history_path)
        if limit is not None:
            records = records[-limit:]
        return records

    def append_history(self, entry: Dict, max_entries: int = 200) -> None:
        records = self._safe_load(self.history_path)
        records.append(entry)
        if max_entries is not None and len(records) > max_entries:
            records = records[-max_entries:]
        self._safe_write(self.history_path, records)

    # ----------------------------
    # Logs
    # ----------------------------
    def load_logs(self, limit: int = 500) -> List[Dict]:
        records = self._safe_load(self.logs_path)
        if limit is not None:
            records = records[-limit:]
        return records

    def append_log(self, entry: Dict, max_entries: int = 500) -> None:
        records = self._safe_load(self.logs_path)
        records.append(entry)
        if max_entries is not None and len(records) > max_entries:
            records = records[-max_entries:]
        self._safe_write(self.logs_path, records)

    def clear_logs(self) -> None:
        """Remove the logs file."""
        try:
            if self.logs_path.exists():
                self.logs_path.unlink()
        except Exception as exc:
            logger.warning("Failed to clear collection logs: %s", exc)

