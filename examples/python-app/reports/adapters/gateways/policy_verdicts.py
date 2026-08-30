from __future__ import annotations

import typing

import tesser.adapters as ts

import linkpolicy.client.client as linkpolicy_client
import reports.application.ports.verdict_source as verdict_source
import tesser.errors as errors

_DECISION_BY_NAME: typing.Final[dict[str, verdict_source.VerdictDecision]] = {
    "allowed": verdict_source.VerdictDecision.ALLOWED,
    "denied": verdict_source.VerdictDecision.DENIED,
}


class PolicyVerdictGateway(ts.Gateway):

    def __init__(self, verdicts: linkpolicy_client.Client) -> None:
        self._verdicts = verdicts

    def verdicts(self, request: verdict_source.ListVerdictsRequest) -> verdict_source.ListVerdictsResponse:
        resp = self._verdicts.list_verdicts(linkpolicy_client.ListVerdictsRequest())
        records: list[verdict_source.VerdictRecord] = []
        for v in resp.verdicts:
            decision = _DECISION_BY_NAME.get(v.decision)
            if decision is None:
                raise errors.InfraError(
                    f"link policy answered decision {v.decision!r}, which is not a verdict"
                )
            records.append(
                verdict_source.VerdictRecord(
                    target_url=v.target_url,
                    decision=decision,
                    reason=v.reason,
                )
            )
        return verdict_source.ListVerdictsResponse(verdicts=tuple(records))
