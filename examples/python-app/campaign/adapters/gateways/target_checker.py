from __future__ import annotations

import tesser.adapters as ts

from campaign.application.parts import CheckOutcome
from linkpolicy.client.client import CheckRequest
from linkpolicy.client.client import Client as LinkPolicyClient


class LinkPolicyTargetChecker(ts.Gateway):

    def __init__(self, policy: LinkPolicyClient) -> None:
        self._policy = policy

    def check(self, target_url: str) -> CheckOutcome:
        resp = self._policy.check(CheckRequest(target_url=target_url))
        return CheckOutcome(allowed=resp.allowed, reason=resp.reason)
