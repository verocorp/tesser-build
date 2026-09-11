from __future__ import annotations

import typing

import tesser.adapters as ts

import campaign.application.ports as ports
import linkpolicy.client as client
import tesser.errors as errors  # tesser:debt TB050

_VERDICT_BY_DECISION: typing.Final[dict[str, ports.PolicyVerdict]] = {
    "allowed": ports.PolicyVerdict.ALLOWED,
    "denied": ports.PolicyVerdict.BLOCKED,
}


class LinkPolicyTargetPolicy(ts.Gateway):

    def __init__(self, link_policy_client: client.LinkPolicyClient) -> None:
        self._link_policy_client = link_policy_client

    def check(
        self, check_target_request: ports.CheckTargetRequest
    ) -> ports.CheckTargetResponse:
        check_response = self._link_policy_client.check(
            client.CheckRequest(target_url=check_target_request.target_url)
        )
        verdict = _VERDICT_BY_DECISION.get(check_response.decision)
        if verdict is None:
            raise errors.InfraError(
                f"link policy answered decision {check_response.decision!r}, which is not a verdict"
            )
        return ports.CheckTargetResponse(verdict=verdict, reason=check_response.reason)
