from __future__ import annotations

import typing

import tesser.adapters as ts

import campaign.application.ports.target_policy as target_policy
import linkpolicy.client.client as linkpolicy_client
import tesser.errors as errors

_VERDICT_BY_DECISION: typing.Final[dict[str, target_policy.PolicyVerdict]] = {
    "allowed": target_policy.PolicyVerdict.ALLOWED,
    "denied": target_policy.PolicyVerdict.BLOCKED,
}


class LinkPolicyTargetPolicy(ts.Gateway):

    def __init__(self, policy: linkpolicy_client.Client) -> None:
        self._policy = policy

    def check(self, request: target_policy.CheckTargetRequest) -> target_policy.CheckTargetResponse:
        resp = self._policy.check(linkpolicy_client.CheckRequest(target_url=request.target_url))
        verdict = _VERDICT_BY_DECISION.get(resp.decision)
        if verdict is None:
            raise errors.InfraError(
                f"link policy answered decision {resp.decision!r}, which is not a verdict"
            )
        return target_policy.CheckTargetResponse(verdict=verdict, reason=resp.reason)
