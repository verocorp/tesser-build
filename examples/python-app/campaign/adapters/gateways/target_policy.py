from __future__ import annotations

import typing

import tesser.adapters as ts

import campaign.application.ports as ports
import linkpolicy.client as linkpolicy_client

_OUTCOME_BY_DECISION: typing.Final[dict[str, ports.CheckTargetOutcome]] = {
    "allowed": ports.CheckTargetOutcome.ALLOWED,
    "denied": ports.CheckTargetOutcome.BLOCKED,
}


class LinkPolicyTargetPolicy(ts.Gateway):

    def __init__(self, link_policy_client: linkpolicy_client.LinkPolicyClient) -> None:
        self._link_policy_client = link_policy_client

    def check_target(
        self, check_target_request: ports.CheckTargetRequest
    ) -> ports.CheckTargetResponse:
        try:
            check_target_response = self._link_policy_client.check_target(
                linkpolicy_client.CheckTargetRequest(target_url=check_target_request.target_url)
            )
        except linkpolicy_client.Unavailable as policy_error:
            raise ports.PolicyUnavailable(policy_error.message) from policy_error
        outcome = _OUTCOME_BY_DECISION.get(check_target_response.decision)
        if outcome is None:
            raise ports.PolicyUnavailable(
                f"link policy answered decision {check_target_response.decision!r}, which is not a verdict"
            )
        return ports.CheckTargetResponse(outcome=outcome, reason=check_target_response.reason)
