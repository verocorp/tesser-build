from __future__ import annotations

import tesser.adapters as ts

import linkpolicy.application.ports as ports
import tesser.errors as errors  # tesser:debt TB050


class InMemoryVerdictRepository(ts.Repository):

    def __init__(self, *, down: bool = False) -> None:
        self._by_url: dict[str, ports.VerdictRecord] = {}
        self._down = down
        self.close_count = 0

    def record(
        self, record_verdict_request: ports.RecordVerdictRequest
    ) -> ports.RecordVerdictResponse:
        if self._down:
            raise errors.InfraError("linkpolicy store unavailable")
        self._by_url[record_verdict_request.target_url] = ports.VerdictRecord(
            target_url=record_verdict_request.target_url,
            decision=record_verdict_request.decision,
            reason=record_verdict_request.reason,
        )
        return ports.RecordVerdictResponse()

    def all(
        self, list_verdicts_request: ports.ListVerdictsRequest
    ) -> ports.ListVerdictsResponse:
        if self._down:
            raise errors.InfraError("linkpolicy store unavailable")
        return ports.ListVerdictsResponse(verdicts=tuple(self._by_url.values()))

    def close(self) -> None:
        self.close_count += 1
