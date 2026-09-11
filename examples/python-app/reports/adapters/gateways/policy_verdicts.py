from __future__ import annotations

import typing

import tesser.adapters as ts

import linkpolicy.client as client
import reports.application.ports as ports
import tesser.errors as errors  # tesser:debt TB050

_DECISION_BY_NAME: typing.Final[dict[str, ports.VerdictDecision]] = {
    "allowed": ports.VerdictDecision.ALLOWED,
    "denied": ports.VerdictDecision.DENIED,
}


class PolicyVerdictGateway(ts.Gateway):

    def __init__(self, link_policy_client: client.LinkPolicyClient) -> None:
        self._link_policy_client = link_policy_client

    def verdicts(
        self, list_verdicts_request: ports.ListVerdictsRequest
    ) -> ports.ListVerdictsResponse:
        list_verdicts_response = self._link_policy_client.list_verdicts(
            client.ListVerdictsRequest()
        )
        records: list[ports.VerdictRecord] = []
        for v in list_verdicts_response.verdicts:
            decision = _DECISION_BY_NAME.get(v.decision)
            if decision is None:
                raise errors.InfraError(
                    f"link policy answered decision {v.decision!r}, which is not a verdict"
                )
            records.append(
                ports.VerdictRecord(
                    target_url=v.target_url,
                    decision=decision,
                    reason=v.reason,
                )
            )
        return ports.ListVerdictsResponse(verdicts=tuple(records))
