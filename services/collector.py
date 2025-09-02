from typing import Protocol, Any

class ContentCollector(Protocol):
    def collect(self) -> list[dict]: ...
