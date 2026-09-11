from __future__ import annotations

import pytest
import tesser.testing as ts

import linkpolicy.client as linkpolicy_client
import reports.adapters.gateways as gateways
import reports.application.ports as ports


@ts.fake
class FakeLinkPolicyClient(linkpolicy_client.LinkPolicyClient):
    def __init__(
        self, *verdicts: linkpolicy_client.VerdictView, error: Exception | None = None
    ) -> None:
        self.verdicts = verdicts
        self.error = error
        self.requests: list[linkpolicy_client.ListVerdictsRequest] = []

    def check(self, check_request: linkpolicy_client.CheckRequest) -> linkpolicy_client.CheckResponse:
        raise AssertionError("check is not part of the reports surface")

    def list_verdicts(
        self, list_verdicts_request: linkpolicy_client.ListVerdictsRequest
    ) -> linkpolicy_client.ListVerdictsResponse:
        self.requests.append(list_verdicts_request)
        if self.error is not None:
            raise self.error
        return linkpolicy_client.ListVerdictsResponse(verdicts=self.verdicts)


def test_an_allowed_verdict_arrives_as_the_allowed_member() -> None:
    fake_link_policy_client = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "allowed", "on the allowlist")
    )

    list_verdicts_response = gateways.PolicyVerdictGateway(fake_link_policy_client).verdicts(
        ports.ListVerdictsRequest()
    )

    assert list_verdicts_response.verdicts[0].decision is ports.VerdictDecision.ALLOWED
    assert list_verdicts_response.verdicts[0].target_url == "https://a.example/s"
    assert list_verdicts_response.verdicts[0].reason == "on the allowlist"


def test_a_denied_verdict_arrives_as_the_denied_member() -> None:
    fake_link_policy_client = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "denied", "host blocked")
    )

    list_verdicts_response = gateways.PolicyVerdictGateway(fake_link_policy_client).verdicts(
        ports.ListVerdictsRequest()
    )

    assert list_verdicts_response.verdicts[0].decision is ports.VerdictDecision.DENIED


def test_every_verdict_the_policy_context_serves_crosses_the_boundary() -> None:
    fake_link_policy_client = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "allowed", "on the allowlist"),
        linkpolicy_client.VerdictView("https://a.example/w", "denied", "host blocked"),
    )

    list_verdicts_response = gateways.PolicyVerdictGateway(fake_link_policy_client).verdicts(
        ports.ListVerdictsRequest()
    )

    assert [record.target_url for record in list_verdicts_response.verdicts] == [
        "https://a.example/s",
        "https://a.example/w",
    ]


def test_the_gateway_asks_the_policy_context_for_its_whole_verdict_list() -> None:
    fake_link_policy_client = FakeLinkPolicyClient()

    gateways.PolicyVerdictGateway(fake_link_policy_client).verdicts(
        ports.ListVerdictsRequest()
    )

    assert len(fake_link_policy_client.requests) == 1
    assert isinstance(fake_link_policy_client.requests[0], linkpolicy_client.ListVerdictsRequest)


def test_a_policy_context_with_no_verdicts_yields_no_records() -> None:
    fake_link_policy_client = FakeLinkPolicyClient()

    list_verdicts_response = gateways.PolicyVerdictGateway(fake_link_policy_client).verdicts(
        ports.ListVerdictsRequest()
    )

    assert list_verdicts_response.verdicts == ()


def test_a_failure_the_policy_context_never_declared_reaches_the_caller() -> None:
    fake_link_policy_client = FakeLinkPolicyClient(error=RuntimeError("policy store unreachable"))

    with pytest.raises(RuntimeError):
        gateways.PolicyVerdictGateway(fake_link_policy_client).verdicts(
            ports.ListVerdictsRequest()
        )


def test_a_policy_context_that_cannot_answer_is_the_ports_unavailable() -> None:
    fake_link_policy_client = FakeLinkPolicyClient(
        error=linkpolicy_client.Unavailable("the verdict store is unavailable")
    )

    with pytest.raises(ports.VerdictSourceUnavailable) as caught:
        gateways.PolicyVerdictGateway(fake_link_policy_client).verdicts(
            ports.ListVerdictsRequest()
        )
    assert isinstance(caught.value.__cause__, linkpolicy_client.Unavailable)


def test_a_verdict_decision_outside_the_recorded_set_is_refused() -> None:
    fake_link_policy_client = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "maybe", "unsure")
    )

    with pytest.raises(ports.VerdictSourceUnavailable):
        gateways.PolicyVerdictGateway(fake_link_policy_client).verdicts(
            ports.ListVerdictsRequest()
        )
