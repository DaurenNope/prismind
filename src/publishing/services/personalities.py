from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict


def load_personalities() -> List[Dict[str, str]]:
    """Load personalities from config/personalities.json.

    Returns a list of dicts with at least a 'key' and optional 'name'. If the
    file is missing or invalid, returns an empty list.
    """
    # Try config path (now in main config directory)
    candidates = [
        Path("config/personalities.json"),
        Path("/Users/mac/Documents/Development/prismind/config/personalities.json"),
    ]
    for p in candidates:
        if p.exists():
            try:
                data = json.loads(p.read_text())
                # Handle both formats: list or dict with "personalities" key
                if isinstance(data, list):
                    return [d for d in data if isinstance(d, dict) and d.get("key")]
                elif isinstance(data, dict) and "personalities" in data:
                    # Convert dict format to list format
                    personalities = data["personalities"]
                    result = []
                    for key, value in personalities.items():
                        if isinstance(value, dict):
                            value["key"] = key  # Add key field
                            result.append(value)
                    return result
            except Exception:
                return []
    return []


def get_persona_keys() -> List[str]:
    items = load_personalities()
    return [i.get("key") for i in items if i.get("key")]
