from typing import Protocol


class ContentCollector(Protocol):
    def collect(self) -> list[dict]: ...
