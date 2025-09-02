from typing import Protocol

class ContentAnalyzer(Protocol):
    def analyze(self, items: list[dict]) -> list[dict]: ...
