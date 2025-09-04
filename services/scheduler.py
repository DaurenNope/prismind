from typing import Callable, Protocol


class Scheduler(Protocol):
    def every_minutes(self, minutes: int, job: Callable[[], None]) -> None: ...
