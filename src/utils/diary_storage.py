import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DIARY_DIR = Path("var")
DIARY_FILE = DIARY_DIR / "diary_entries.json"


@dataclass
class DiaryEntry:
    timestamp: str
    profile_key: Optional[str]
    shipped: str
    blockers: Optional[str]
    focus: Optional[str]
    tags: Optional[List[str]]
    extra: Optional[Dict[str, Any]] = None


class DiaryStorage:
    """
    Lightweight JSON-backed storage for builder diary entries.
    """

    def __init__(self, file_path: Path = DIARY_FILE):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write([])

    def _read(self) -> List[Dict[str, Any]]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error: {e}")
            return []

    def _write(self, data: List[Dict[str, Any]]) -> None:
        tmp_path = str(self.file_path) + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.file_path)

    def add_entry(
        self,
        shipped: str,
        profile_key: Optional[str] = None,
        blockers: Optional[str] = None,
        focus: Optional[str] = None,
        tags: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> DiaryEntry:
        entry = DiaryEntry(
            timestamp=timestamp or datetime.utcnow().isoformat(),
            profile_key=profile_key,
            shipped=shipped.strip(),
            blockers=(blockers or "").strip() or None,
            focus=(focus or "").strip() or None,
            tags=[t.strip() for t in (tags or []) if t and t.strip()] or None,
            extra=extra or None,
        )
        data = self._read()
        data.append(asdict(entry))
        self._write(data)
        return entry

    def load_entries(
        self,
        profile_key: Optional[str] = None,
        limit: Optional[int] = 50,
        reverse: bool = True,
    ) -> List[Dict[str, Any]]:
        data = self._read()
        if profile_key:
            data = [d for d in data if d.get("profile_key") == profile_key]
        # sort by timestamp
        data.sort(key=lambda d: d.get("timestamp") or "", reverse=reverse)
        if limit:
            return data[:limit]
        return data
