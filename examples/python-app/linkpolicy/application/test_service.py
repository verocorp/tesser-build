from __future__ import annotations

import pytest
import tesser.testing as ts

import linkpolicy.application.ports.verdict_repository as verdict_repository
import linkpolicy.application.service as service
import linkpolicy.client.client as client
import tesser.errors as errors


@ts.fake
class FakeVerdictRepository(verdict_repository.VerdictRepository):
    def __init__(
        self,
        *records: verdict_repository.VerdictRecord,
        error: Exception | None = None,
    ) -> None:
        self.records = list(records)
        self.error = error

    def record(
        self, request: verdict_repository.RecordVerdictRequest
    ) -> verdict_repository.RecordVerdictResponse:
        if self.error is not None:
            raise self.error
        self.records.append(
            verdict_repository.VerdictRecord(
                target_url=request.target_url,
                decision=request.decision,
                reason=request.reason,
            )
        )
        return verdict_repository.RecordVerdictResponse()

    def all(
        self, request: verdict_repository.ListVerdictsRequest
    ) -> verdict_repository.ListVerdictsResponse:
        if self.error is not None:
            raise self.error
        return verdict_repository.ListVerdictsResponse(verdicts=tuple(self.records))


def test_check_allows_a_url_the_policy_permits() -> None:
    subject = service.LinkPolicyService(FakeVerdictRepository())

    resp = subject.check(client.CheckRequest("https://ok.example/x"))

    assert resp.allowed is True
    assert resp.reason == "ok"


def test_check_denies_a_url_whose_scheme_is_not_allowed() -> None:
    subject = service.LinkPolicyService(FakeVerdictRepository())

    resp = subject.check(client.CheckRequest("http://ok.example/x"))

    assert resp.allowed is False
    assert resp.reason == "scheme 'http' not allowed"


def test_check_denies_a_url_on_a_blocked_host() -> None:
    subject = service.LinkPolicyService(FakeVerdictRepository())

    resp = subject.check(client.CheckRequest("https://evil.example/x"))

    assert resp.allowed is False
    assert resp.reason == "host 'evil.example' is blocked"


def test_check_records_the_allowed_verdict_it_returned() -> None:
    repo = FakeVerdictRepository()

    service.LinkPolicyService(repo).check(client.CheckRequest("https://ok.example/x"))

    assert len(repo.records) == 1
    assert repo.records[0].target_url == "https://ok.example/x"
    assert repo.records[0].decision is verdict_repository.VerdictDecision.ALLOWED
    assert repo.records[0].reason == "ok"


def test_check_records_a_denial_as_the_denied_decision() -> None:
    repo = FakeVerdictRepository()

    service.LinkPolicyService(repo).check(client.CheckRequest("https://evil.example/x"))

    assert repo.records[0].decision is verdict_repository.VerdictDecision.DENIED
    assert repo.records[0].reason == "host 'evil.example' is blocked"


def test_check_propagates_a_repository_failure() -> None:
    repo = FakeVerdictRepository(error=errors.InfraError("linkpolicy store unavailable"))

    with pytest.raises(errors.InfraError):
        service.LinkPolicyService(repo).check(client.CheckRequest("https://ok.example/x"))


def test_list_verdicts_answers_nothing_when_nothing_was_recorded() -> None:
    subject = service.LinkPolicyService(FakeVerdictRepository())

    resp = subject.list_verdicts(client.ListVerdictsRequest())

    assert resp.verdicts == ()


def test_list_verdicts_maps_every_record_to_a_view() -> None:
    repo = FakeVerdictRepository(
        verdict_repository.VerdictRecord(
            "https://ok.example/x", verdict_repository.VerdictDecision.ALLOWED, "ok"
        ),
        verdict_repository.VerdictRecord(
            "https://bad.example/y",
            verdict_repository.VerdictDecision.DENIED,
            "host 'bad.example' is blocked",
        ),
    )

    resp = service.LinkPolicyService(repo).list_verdicts(client.ListVerdictsRequest())

    assert [(v.target_url, v.allowed, v.reason) for v in resp.verdicts] == [
        ("https://ok.example/x", True, "ok"),
        ("https://bad.example/y", False, "host 'bad.example' is blocked"),
    ]


def test_list_verdicts_returns_what_check_recorded() -> None:
    repo = FakeVerdictRepository()
    subject = service.LinkPolicyService(repo)

    subject.check(client.CheckRequest("https://ok.example/x"))
    resp = subject.list_verdicts(client.ListVerdictsRequest())

    assert [(v.target_url, v.allowed) for v in resp.verdicts] == [
        ("https://ok.example/x", True)
    ]


def test_list_verdicts_propagates_a_repository_failure() -> None:
    repo = FakeVerdictRepository(error=errors.InfraError("linkpolicy store unavailable"))

    with pytest.raises(errors.InfraError):
        service.LinkPolicyService(repo).list_verdicts(client.ListVerdictsRequest())


def test_check_refuses_an_empty_url_and_records_nothing() -> None:
    repo = FakeVerdictRepository()
    with pytest.raises(errors.DomainError) as ei:
        service.LinkPolicyService(repo).check(client.CheckRequest(""))
    assert ei.value.code == "invalid_target_url"
    assert repo.records == []
