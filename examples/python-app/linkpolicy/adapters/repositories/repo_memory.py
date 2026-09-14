from __future__ import annotations

import tesser.adapters as ts

import linkpolicy.application.ports as ports


class InMemoryVerdictRepository(ts.Repository):

    def __init__(self) -> None:
        self._by_url: dict[str, ports.VerdictRecord] = {}
        self.close_count = 0

    def record_verdict(
        self, record_verdict_request: ports.RecordVerdictRequest
    ) -> ports.RecordVerdictResponse:
        self._by_url[record_verdict_request.target_url] = ports.VerdictRecord(
            target_url=record_verdict_request.target_url,
            decision=record_verdict_request.decision,
            reason=record_verdict_request.reason,
        )
        return ports.RecordVerdictResponse()

    def list_verdicts(
        self, list_verdicts_request: ports.ListVerdictsRequest
    ) -> ports.ListVerdictsResponse:
        return ports.ListVerdictsResponse(verdicts=tuple(self._by_url.values()))

    def close(self) -> None:
        self.close_count += 1
