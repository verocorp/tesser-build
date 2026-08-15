from __future__ import annotations

import tesser.adapters as ts

from tesser.errors import InfraError
import linkpolicy.application.ports.verdict_repository as verdict_repository


class InMemoryVerdictRepository(ts.Repository):

    def __init__(self, *, down: bool = False) -> None:
        self._by_url: dict[str, verdict_repository.VerdictRecord] = {}
        self._down = down
        self.close_count = 0

    def record(
        self, request: verdict_repository.RecordVerdictRequest
    ) -> verdict_repository.RecordVerdictResponse:
        if self._down:
            raise InfraError("linkpolicy store unavailable")
        self._by_url[request.target_url] = verdict_repository.VerdictRecord(
            target_url=request.target_url, decision=request.decision, reason=request.reason
        )
        return verdict_repository.RecordVerdictResponse()

    def all(
        self, request: verdict_repository.ListVerdictsRequest
    ) -> verdict_repository.ListVerdictsResponse:
        if self._down:
            raise InfraError("linkpolicy store unavailable")
        return verdict_repository.ListVerdictsResponse(verdicts=tuple(self._by_url.values()))

    def close(self) -> None:
        self.close_count += 1
