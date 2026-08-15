from __future__ import annotations

import tesser.testing as ts

import campaign.adapters.gateways.target_policy as target_policy
import campaign.application.ports.target_policy as port
import linkpolicy.client.client as linkpolicy_client


@ts.fake
class SampledPolicyClient(linkpolicy_client.Client):

    def __init__(self, allowed: bool, reason: str) -> None:
        self._allowed = allowed
        self._reason = reason
        self.checked: list[str] = []

    def check(self, req: linkpolicy_client.CheckRequest) -> linkpolicy_client.CheckResponse:
        self.checked.append(req.target_url)
        return linkpolicy_client.CheckResponse(allowed=self._allowed, reason=self._reason)

    def list_verdicts(
        self, req: linkpolicy_client.ListVerdictsRequest
    ) -> linkpolicy_client.ListVerdictsResponse:
        return linkpolicy_client.ListVerdictsResponse(verdicts=())


def test_a_sampled_allow_maps_to_the_allowed_verdict() -> None:
    gateway = target_policy.LinkPolicyTargetPolicy(SampledPolicyClient(True, "clean"))
    response = gateway.check(port.CheckTargetRequest(target_url="https://ok.example"))
    assert response.verdict is port.PolicyVerdict.ALLOWED
    assert response.reason == "clean"


def test_a_sampled_block_maps_to_the_blocked_verdict() -> None:
    gateway = target_policy.LinkPolicyTargetPolicy(SampledPolicyClient(False, "listed"))
    response = gateway.check(port.CheckTargetRequest(target_url="https://bad.example"))
    assert response.verdict is port.PolicyVerdict.BLOCKED
    assert response.reason == "listed"
