from __future__ import annotations

import tesser.adapters as ts

import campaign.application.parts as parts
import linkpolicy.client.client as linkpolicy_client


class LinkPolicyTargetPolicy(ts.Gateway):

    def __init__(self, policy: linkpolicy_client.Client) -> None:
        self._policy = policy

    def check(self, target_url: str) -> parts.PolicyOutcome:
        resp = self._policy.check(linkpolicy_client.CheckRequest(target_url=target_url))
        return parts.PolicyOutcome(allowed=resp.allowed, reason=resp.reason)
