from typing import Protocol, Callable

class Scheduler(Protocol):
    def every_minutes(self, minutes: int, job: Callable[[], None]) -> None: ...
