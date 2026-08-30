from __future__ import annotations

import tesser.testing as ts

import campaign.adapters.gateways.target_policy as target_policy
import campaign.application.ports.target_policy as port
import linkpolicy.client.client as linkpolicy_client


@ts.fake
class RecordingPolicyClient(linkpolicy_client.Client):

    def __init__(self, decision: str, reason: str) -> None:
        self._decision = decision
        self._reason = reason
        self.asked: list[str] = []

    def check(self, req: linkpolicy_client.CheckRequest) -> linkpolicy_client.CheckResponse:
        self.asked.append(req.target_url)
        return linkpolicy_client.CheckResponse(decision=self._decision, reason=self._reason)

    def list_verdicts(
        self, req: linkpolicy_client.ListVerdictsRequest
    ) -> linkpolicy_client.ListVerdictsResponse:
        return linkpolicy_client.ListVerdictsResponse(verdicts=())


def test_an_allowed_neighbour_verdict_becomes_the_allowed_verdict() -> None:
    gateway = target_policy.LinkPolicyTargetPolicy(RecordingPolicyClient("allowed", "clean"))

    response = gateway.check(port.CheckTargetRequest(target_url="https://ok.example/x"))

    assert response.verdict is port.PolicyVerdict.ALLOWED
    assert response.reason == "clean"


def test_a_blocked_neighbour_verdict_becomes_the_blocked_verdict() -> None:
    gateway = target_policy.LinkPolicyTargetPolicy(RecordingPolicyClient("denied", "on the list"))

    response = gateway.check(port.CheckTargetRequest(target_url="https://bad.example/x"))

    assert response.verdict is port.PolicyVerdict.BLOCKED
    assert response.reason == "on the list"


def test_the_target_url_reaches_the_neighbour_unchanged() -> None:
    client = RecordingPolicyClient("allowed", "clean")
    gateway = target_policy.LinkPolicyTargetPolicy(client)

    gateway.check(port.CheckTargetRequest(target_url="https://ok.example/a?b=1#c"))

    assert client.asked == ["https://ok.example/a?b=1#c"]


def test_an_empty_neighbour_reason_is_carried_through_rather_than_invented() -> None:
    gateway = target_policy.LinkPolicyTargetPolicy(RecordingPolicyClient("allowed", ""))

    assert gateway.check(port.CheckTargetRequest(target_url="https://ok.example/x")).reason == ""


def test_the_gateway_asks_the_neighbour_once_per_check() -> None:
    client = RecordingPolicyClient("allowed", "clean")
    gateway = target_policy.LinkPolicyTargetPolicy(client)

    gateway.check(port.CheckTargetRequest(target_url="https://ok.example/a"))
    gateway.check(port.CheckTargetRequest(target_url="https://ok.example/b"))

    assert client.asked == ["https://ok.example/a", "https://ok.example/b"]
