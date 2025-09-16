from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict


class WebhookNotifier:
    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("WEBHOOK_URL", "")

    def enabled(self) -> bool:
        return bool(self.url)

    def notify(self, payload: Dict[str, Any]) -> bool:
        if not self.enabled():
            return False
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - simple webhook
                return 200 <= resp.status < 300
        except Exception:
            return False


