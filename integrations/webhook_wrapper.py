from typing import Callable, Any

class WebhookClient:
    def __init__(self, sender: Callable[[str, dict], Any]):
        self._send = sender

    def post(self, url: str, payload: dict) -> Any:
        return self._send(url, payload)
