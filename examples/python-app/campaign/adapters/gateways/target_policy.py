from __future__ import annotations

import tesser.adapters as ts

import campaign.application.ports.target_policy as target_policy
import linkpolicy.client.client as linkpolicy_client


class LinkPolicyTargetPolicy(ts.Gateway):

    def __init__(self, policy: linkpolicy_client.Client) -> None:
        self._policy = policy

    def check(self, request: target_policy.CheckTargetRequest) -> target_policy.CheckTargetResponse:
        resp = self._policy.check(linkpolicy_client.CheckRequest(target_url=request.target_url))
        verdict = target_policy.PolicyVerdict.ALLOWED if resp.allowed else target_policy.PolicyVerdict.BLOCKED
        return target_policy.CheckTargetResponse(verdict=verdict, reason=resp.reason)
