from typing import Protocol


class Notifier(Protocol):
    def notify(self, messages: list[str]) -> None: ...
