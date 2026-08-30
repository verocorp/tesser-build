from __future__ import annotations

import pytest
import tesser.testing as ts

import linkpolicy.client.client as linkpolicy_client
import reports.adapters.gateways.policy_verdicts as policy_verdicts
import reports.application.ports.verdict_source as verdict_source
import tesser.errors as errors


@ts.fake
class FakeLinkPolicyClient(linkpolicy_client.Client):
    def __init__(
        self, *verdicts: linkpolicy_client.VerdictView, error: Exception | None = None
    ) -> None:
        self.verdicts = verdicts
        self.error = error
        self.requests: list[linkpolicy_client.ListVerdictsRequest] = []

    def check(self, req: linkpolicy_client.CheckRequest) -> linkpolicy_client.CheckResponse:
        raise AssertionError("check is not part of the reports surface")

    def list_verdicts(
        self, req: linkpolicy_client.ListVerdictsRequest
    ) -> linkpolicy_client.ListVerdictsResponse:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        return linkpolicy_client.ListVerdictsResponse(verdicts=self.verdicts)


def test_an_allowed_verdict_arrives_as_the_allowed_member() -> None:
    verdicts = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "allowed", "on the allowlist")
    )

    resp = policy_verdicts.PolicyVerdictGateway(verdicts).verdicts(
        verdict_source.ListVerdictsRequest()
    )

    assert resp.verdicts[0].decision is verdict_source.VerdictDecision.ALLOWED
    assert resp.verdicts[0].target_url == "https://a.example/s"
    assert resp.verdicts[0].reason == "on the allowlist"


def test_a_denied_verdict_arrives_as_the_denied_member() -> None:
    verdicts = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "denied", "host blocked")
    )

    resp = policy_verdicts.PolicyVerdictGateway(verdicts).verdicts(
        verdict_source.ListVerdictsRequest()
    )

    assert resp.verdicts[0].decision is verdict_source.VerdictDecision.DENIED


def test_every_verdict_the_policy_context_serves_crosses_the_boundary() -> None:
    verdicts = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "allowed", "on the allowlist"),
        linkpolicy_client.VerdictView("https://a.example/w", "denied", "host blocked"),
    )

    resp = policy_verdicts.PolicyVerdictGateway(verdicts).verdicts(
        verdict_source.ListVerdictsRequest()
    )

    assert [record.target_url for record in resp.verdicts] == [
        "https://a.example/s",
        "https://a.example/w",
    ]


def test_the_gateway_asks_the_policy_context_for_its_whole_verdict_list() -> None:
    verdicts = FakeLinkPolicyClient()

    policy_verdicts.PolicyVerdictGateway(verdicts).verdicts(
        verdict_source.ListVerdictsRequest()
    )

    assert len(verdicts.requests) == 1
    assert isinstance(verdicts.requests[0], linkpolicy_client.ListVerdictsRequest)


def test_a_policy_context_with_no_verdicts_yields_no_records() -> None:
    verdicts = FakeLinkPolicyClient()

    resp = policy_verdicts.PolicyVerdictGateway(verdicts).verdicts(
        verdict_source.ListVerdictsRequest()
    )

    assert resp.verdicts == ()


def test_a_failure_inside_the_policy_context_reaches_the_caller() -> None:
    verdicts = FakeLinkPolicyClient(error=errors.InfraError("policy store unreachable"))

    with pytest.raises(errors.InfraError):
        policy_verdicts.PolicyVerdictGateway(verdicts).verdicts(
            verdict_source.ListVerdictsRequest()
        )


def test_a_verdict_decision_outside_the_recorded_set_is_refused() -> None:
    verdicts = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "maybe", "unsure")
    )

    with pytest.raises(ValueError):
        policy_verdicts.PolicyVerdictGateway(verdicts).verdicts(
            verdict_source.ListVerdictsRequest()
        )
