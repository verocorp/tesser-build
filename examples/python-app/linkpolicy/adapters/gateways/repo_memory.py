from __future__ import annotations

import tesser.adapters as ts

from errors import InfraError
from linkpolicy.application.service import VerdictParts


class InMemoryVerdictRepository(ts.Repository):

    def __init__(self, *, down: bool = False) -> None:
        self._by_url: dict[str, VerdictParts] = {}
        self._down = down
        self.close_count = 0

    def record(self, parts: VerdictParts) -> None:
        if self._down:
            raise InfraError("linkpolicy store unavailable")
        self._by_url[parts.target_url] = parts

    def all(self) -> tuple[VerdictParts, ...]:
        if self._down:
            raise InfraError("linkpolicy store unavailable")
        return tuple(self._by_url.values())

    def close(self) -> None:
        self.close_count += 1
