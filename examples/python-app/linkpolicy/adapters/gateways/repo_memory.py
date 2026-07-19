from __future__ import annotations

from errors import InfraError
from linkpolicy.domain.policy import Verdict


class InMemoryVerdictRepository:
    def __init__(self, *, down: bool = False) -> None:
        self._by_url: dict[str, Verdict] = {}
        self._down = down
        self.close_count = 0

    def record(self, verdict: Verdict) -> None:
        if self._down:
            raise InfraError("linkpolicy store unavailable")
        self._by_url[verdict.target_url] = verdict

    def all(self) -> tuple[Verdict, ...]:
        if self._down:
            raise InfraError("linkpolicy store unavailable")
        return tuple(self._by_url.values())

    def close(self) -> None:
        self.close_count += 1
