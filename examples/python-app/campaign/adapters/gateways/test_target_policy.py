from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.adapters.gateways as gateways
import campaign.application.ports as ports
import linkpolicy.client as client


@ts.fake
class RecordingPolicyClient(client.LinkPolicyClient):

    def __init__(self, decision: str, reason: str) -> None:
        self._decision = decision
        self._reason = reason
        self.asked: list[str] = []

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        self.asked.append(check_request.target_url)
        return client.CheckResponse(decision=self._decision, reason=self._reason)

    def list_verdicts(
        self, list_verdicts_request: client.ListVerdictsRequest
    ) -> client.ListVerdictsResponse:
        return client.ListVerdictsResponse(verdicts=())


def test_an_allowed_neighbour_verdict_becomes_the_allowed_verdict() -> None:
    link_policy_target_policy = gateways.LinkPolicyTargetPolicy(
        RecordingPolicyClient("allowed", "clean")
    )

    check_target_response = link_policy_target_policy.check(
        ports.CheckTargetRequest(target_url="https://ok.example/x")
    )

    assert check_target_response.verdict is ports.PolicyVerdict.ALLOWED
    assert check_target_response.reason == "clean"


def test_a_blocked_neighbour_verdict_becomes_the_blocked_verdict() -> None:
    link_policy_target_policy = gateways.LinkPolicyTargetPolicy(
        RecordingPolicyClient("denied", "on the list")
    )

    check_target_response = link_policy_target_policy.check(
        ports.CheckTargetRequest(target_url="https://bad.example/x")
    )

    assert check_target_response.verdict is ports.PolicyVerdict.BLOCKED
    assert check_target_response.reason == "on the list"


def test_the_target_url_reaches_the_neighbour_unchanged() -> None:
    recording_policy_client = RecordingPolicyClient("allowed", "clean")
    link_policy_target_policy = gateways.LinkPolicyTargetPolicy(recording_policy_client)

    link_policy_target_policy.check(
        ports.CheckTargetRequest(target_url="https://ok.example/a?b=1#c")
    )

    assert recording_policy_client.asked == ["https://ok.example/a?b=1#c"]


def test_an_empty_neighbour_reason_is_carried_through_rather_than_invented() -> None:
    link_policy_target_policy = gateways.LinkPolicyTargetPolicy(
        RecordingPolicyClient("allowed", "")
    )

    check_target_response = link_policy_target_policy.check(
        ports.CheckTargetRequest(target_url="https://ok.example/x")
    )

    assert check_target_response.reason == ""


def test_the_gateway_asks_the_neighbour_once_per_check() -> None:
    recording_policy_client = RecordingPolicyClient("allowed", "clean")
    link_policy_target_policy = gateways.LinkPolicyTargetPolicy(recording_policy_client)

    link_policy_target_policy.check(ports.CheckTargetRequest(target_url="https://ok.example/a"))
    link_policy_target_policy.check(ports.CheckTargetRequest(target_url="https://ok.example/b"))

    assert recording_policy_client.asked == ["https://ok.example/a", "https://ok.example/b"]


def test_a_neighbour_decision_the_gateway_knows_no_verdict_for_is_refused() -> None:
    link_policy_target_policy = gateways.LinkPolicyTargetPolicy(
        RecordingPolicyClient("maybe", "unsure")
    )

    with pytest.raises(ports.PolicyUnavailable):
        link_policy_target_policy.check(
            ports.CheckTargetRequest(target_url="https://ok.example/x")
        )
