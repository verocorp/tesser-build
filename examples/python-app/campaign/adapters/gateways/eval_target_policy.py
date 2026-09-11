from __future__ import annotations

import tesser.testing as ts

import campaign.adapters.gateways as gateways
import campaign.application.ports as ports
import linkpolicy.client as linkpolicy_client


@ts.fake
class SampledPolicyClient(linkpolicy_client.LinkPolicyClient):

    def __init__(self, decision: str, reason: str) -> None:
        self._decision = decision
        self._reason = reason
        self.checked: list[str] = []

    def check(self, check_request: linkpolicy_client.CheckRequest) -> linkpolicy_client.CheckResponse:
        self.checked.append(check_request.target_url)
        return linkpolicy_client.CheckResponse(decision=self._decision, reason=self._reason)

    def list_verdicts(
        self, list_verdicts_request: linkpolicy_client.ListVerdictsRequest
    ) -> linkpolicy_client.ListVerdictsResponse:
        return linkpolicy_client.ListVerdictsResponse(verdicts=())


def test_a_sampled_allow_maps_to_the_allowed_verdict() -> None:
    link_policy_target_policy = gateways.LinkPolicyTargetPolicy(
        SampledPolicyClient("allowed", "clean")
    )

    check_target_response = link_policy_target_policy.check(
        ports.CheckTargetRequest(target_url="https://ok.example")
    )

    assert check_target_response.verdict is ports.PolicyVerdict.ALLOWED
    assert check_target_response.reason == "clean"


def test_a_sampled_block_maps_to_the_blocked_verdict() -> None:
    link_policy_target_policy = gateways.LinkPolicyTargetPolicy(
        SampledPolicyClient("denied", "listed")
    )

    check_target_response = link_policy_target_policy.check(
        ports.CheckTargetRequest(target_url="https://bad.example")
    )

    assert check_target_response.verdict is ports.PolicyVerdict.BLOCKED
    assert check_target_response.reason == "listed"
