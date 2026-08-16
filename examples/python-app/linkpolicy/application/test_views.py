from __future__ import annotations

import linkpolicy.application.ports.verdict_repository as verdict_repository
import linkpolicy.application.views as views
import linkpolicy.client.client as client
import linkpolicy.domain.policy as policy


def test_record_request_carries_the_verdict_of_an_allowed_url() -> None:
    request = views.record_request(policy.Verdict("https://ok.example/x", True, "ok"))

    assert request.target_url == "https://ok.example/x"
    assert request.decision is verdict_repository.VerdictDecision.ALLOWED
    assert request.reason == "ok"


def test_record_request_carries_the_denied_decision_of_a_denied_verdict() -> None:
    request = views.record_request(
        policy.Verdict("https://bad.example/y", False, "host 'bad.example' is blocked")
    )

    assert request.target_url == "https://bad.example/y"
    assert request.decision is verdict_repository.VerdictDecision.DENIED
    assert request.reason == "host 'bad.example' is blocked"


def test_check_response_reports_an_allowed_verdict_as_true() -> None:
    response = views.check_response(policy.Verdict("https://ok.example/x", True, "ok"))

    assert response.allowed is True
    assert response.reason == "ok"


def test_check_response_reports_a_denied_verdict_as_false() -> None:
    response = views.check_response(
        policy.Verdict("https://bad.example/y", False, "host 'bad.example' is blocked")
    )

    assert response.allowed is False
    assert response.reason == "host 'bad.example' is blocked"


def test_verdict_view_reports_an_allowed_record_as_true() -> None:
    view = views.verdict_view(
        verdict_repository.VerdictRecord(
            "https://ok.example/x", verdict_repository.VerdictDecision.ALLOWED, "ok"
        )
    )

    assert isinstance(view, client.VerdictView)
    assert view.target_url == "https://ok.example/x"
    assert view.allowed is True
    assert view.reason == "ok"


def test_verdict_view_reports_a_denied_record_as_false() -> None:
    view = views.verdict_view(
        verdict_repository.VerdictRecord(
            "https://bad.example/y",
            verdict_repository.VerdictDecision.DENIED,
            "host 'bad.example' is blocked",
        )
    )

    assert view.target_url == "https://bad.example/y"
    assert view.allowed is False
    assert view.reason == "host 'bad.example' is blocked"


def test_a_verdict_round_trips_from_the_record_request_to_the_view() -> None:
    request = views.record_request(policy.Verdict("https://ok.example/x", True, "ok"))

    view = views.verdict_view(
        verdict_repository.VerdictRecord(
            request.target_url, request.decision, request.reason
        )
    )

    assert view.target_url == request.target_url
    assert view.allowed is True
    assert view.reason == request.reason
