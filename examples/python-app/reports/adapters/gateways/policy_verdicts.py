from __future__ import annotations

import typing

import tesser.adapters as ts

import linkpolicy.client as linkpolicy_client
import reports.application.ports as ports

_DECISION_BY_NAME: typing.Final[dict[str, ports.VerdictDecision]] = {
    "allowed": ports.VerdictDecision.ALLOWED,
    "denied": ports.VerdictDecision.DENIED,
}


class PolicyVerdictGateway(ts.Gateway):

    def __init__(self, link_policy_client: linkpolicy_client.LinkPolicyClient) -> None:
        self._link_policy_client = link_policy_client

    def list_verdicts(
        self, list_verdicts_request: ports.ListVerdictsRequest
    ) -> ports.ListVerdictsResponse:
        list_verdicts_response = self._link_policy_client.list_verdicts(
            linkpolicy_client.ListVerdictsRequest()
        )
        records: list[ports.VerdictRecord] = []
        for v in list_verdicts_response.verdicts:
            records.append(
                ports.VerdictRecord(
                    target_url=v.target_url,
                    decision=_DECISION_BY_NAME[v.decision],
                    reason=v.reason,
                )
            )
        return ports.ListVerdictsResponse(verdicts=tuple(records))
