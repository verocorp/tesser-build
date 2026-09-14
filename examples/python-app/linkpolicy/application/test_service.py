from __future__ import annotations

import pytest
import tesser.testing as ts

import linkpolicy.application as application
import linkpolicy.application.ports as ports
import linkpolicy.client as client


@ts.fake
class FakeVerdictRepository(ports.VerdictRepository):
    def __init__(self, *records: ports.VerdictRecord) -> None:
        self.records = list(records)

    def record_verdict(
        self, record_verdict_request: ports.RecordVerdictRequest
    ) -> ports.RecordVerdictResponse:
        self.records.append(
            ports.VerdictRecord(
                target_url=record_verdict_request.target_url,
                decision=record_verdict_request.decision,
                reason=record_verdict_request.reason,
            )
        )
        return ports.RecordVerdictResponse()

    def list_verdicts(
        self, list_verdicts_request: ports.ListVerdictsRequest
    ) -> ports.ListVerdictsResponse:
        return ports.ListVerdictsResponse(verdicts=tuple(self.records))


def test_check_allows_a_url_the_policy_permits() -> None:
    link_policy_service = application.LinkPolicyService(FakeVerdictRepository())

    check_target_response = link_policy_service.check_target(client.CheckTargetRequest("https://ok.example/x"))

    assert check_target_response.decision == "allowed"
    assert check_target_response.reason == "ok"


def test_check_denies_a_url_whose_scheme_is_not_allowed() -> None:
    link_policy_service = application.LinkPolicyService(FakeVerdictRepository())

    check_target_response = link_policy_service.check_target(client.CheckTargetRequest("http://ok.example/x"))

    assert check_target_response.decision == "denied"
    assert check_target_response.reason == "scheme 'http' not allowed"


def test_check_denies_a_url_on_a_blocked_host() -> None:
    link_policy_service = application.LinkPolicyService(FakeVerdictRepository())

    check_target_response = link_policy_service.check_target(client.CheckTargetRequest("https://evil.example/x"))

    assert check_target_response.decision == "denied"
    assert check_target_response.reason == "host 'evil.example' is blocked"


def test_check_records_the_allowed_verdict_it_returned() -> None:
    fake_verdict_repository = FakeVerdictRepository()

    application.LinkPolicyService(fake_verdict_repository).check_target(
        client.CheckTargetRequest("https://ok.example/x")
    )

    assert len(fake_verdict_repository.records) == 1
    assert fake_verdict_repository.records[0].target_url == "https://ok.example/x"
    assert fake_verdict_repository.records[0].decision is ports.VerdictDecision.ALLOWED
    assert fake_verdict_repository.records[0].reason == "ok"


def test_check_records_a_denial_as_the_denied_decision() -> None:
    fake_verdict_repository = FakeVerdictRepository()

    application.LinkPolicyService(fake_verdict_repository).check_target(
        client.CheckTargetRequest("https://evil.example/x")
    )

    assert fake_verdict_repository.records[0].decision is ports.VerdictDecision.DENIED
    assert fake_verdict_repository.records[0].reason == "host 'evil.example' is blocked"


def test_list_verdicts_answers_nothing_when_nothing_was_recorded() -> None:
    link_policy_service = application.LinkPolicyService(FakeVerdictRepository())

    list_verdicts_response = link_policy_service.list_verdicts(client.ListVerdictsRequest())

    assert list_verdicts_response.verdicts == ()


def test_list_verdicts_maps_every_record_to_a_view() -> None:
    fake_verdict_repository = FakeVerdictRepository(
        ports.VerdictRecord("https://ok.example/x", ports.VerdictDecision.ALLOWED, "ok"),
        ports.VerdictRecord(
            "https://bad.example/y",
            ports.VerdictDecision.DENIED,
            "host 'bad.example' is blocked",
        ),
    )

    list_verdicts_response = application.LinkPolicyService(
        fake_verdict_repository
    ).list_verdicts(client.ListVerdictsRequest())

    assert [
        (v.target_url, v.decision, v.reason) for v in list_verdicts_response.verdicts
    ] == [
        ("https://ok.example/x", "allowed", "ok"),
        ("https://bad.example/y", "denied", "host 'bad.example' is blocked"),
    ]


def test_list_verdicts_returns_what_check_recorded() -> None:
    fake_verdict_repository = FakeVerdictRepository()
    link_policy_service = application.LinkPolicyService(fake_verdict_repository)

    link_policy_service.check_target(client.CheckTargetRequest("https://ok.example/x"))
    list_verdicts_response = link_policy_service.list_verdicts(client.ListVerdictsRequest())

    assert [(v.target_url, v.decision) for v in list_verdicts_response.verdicts] == [
        ("https://ok.example/x", "allowed")
    ]


def test_check_refuses_an_empty_url_and_records_nothing() -> None:
    fake_verdict_repository = FakeVerdictRepository()
    with pytest.raises(client.TargetRejected) as ei:
        application.LinkPolicyService(fake_verdict_repository).check_target(client.CheckTargetRequest(""))
    assert ei.value.code == "invalid_target_url"
    assert fake_verdict_repository.records == []
