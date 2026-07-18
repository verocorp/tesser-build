"""The cross-context adapter: satisfies campaign's OWN ``TargetChecker`` port by
calling the ``linkpolicy.Client``. It lives HERE, in campaign's gateways — the
CONSUMER owns the adapter — so the dependency runs one way (campaign -> linkpolicy)
and linkpolicy stays ignorant of campaign.

It is an anti-corruption seam: it translates linkpolicy's ``CheckResponse`` into
campaign's own ``CheckOutcome``, so linkpolicy's vocabulary never crosses inward.
An ``InfraError`` raised by linkpolicy (its store is down) propagates untouched —
that is the fail-closed coupling.
"""

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
