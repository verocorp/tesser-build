from __future__ import annotations

from campaign.client import CheckOutcome
from linkpolicy import CheckRequest
from linkpolicy import Client as LinkPolicyClient


class LinkPolicyTargetChecker:
    def __init__(self, policy: LinkPolicyClient) -> None:
        self._policy = policy

    def check(self, target_url: str) -> CheckOutcome:
        resp = self._policy.check(CheckRequest(target_url=target_url))
        return CheckOutcome(allowed=resp.allowed, reason=resp.reason)
