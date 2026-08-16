from __future__ import annotations

import pytest

import linkpolicy.adapters.gateways.repo_memory as repo_memory
import linkpolicy.application.ports.verdict_repository as verdict_repository
from tesser.errors import InfraError


def test_all_answers_nothing_before_anything_is_recorded() -> None:
    subject = repo_memory.InMemoryVerdictRepository()

    listed = subject.all(verdict_repository.ListVerdictsRequest())

    assert listed.verdicts == ()


def test_a_recorded_verdict_comes_back_from_all() -> None:
    subject = repo_memory.InMemoryVerdictRepository()

    subject.record(
        verdict_repository.RecordVerdictRequest(
            "https://ok.example/x", verdict_repository.VerdictDecision.ALLOWED, "ok"
        )
    )
    listed = subject.all(verdict_repository.ListVerdictsRequest())

    assert [(v.target_url, v.decision, v.reason) for v in listed.verdicts] == [
        ("https://ok.example/x", verdict_repository.VerdictDecision.ALLOWED, "ok")
    ]


def test_all_keeps_the_order_the_urls_were_first_recorded_in() -> None:
    subject = repo_memory.InMemoryVerdictRepository()

    subject.record(
        verdict_repository.RecordVerdictRequest(
            "https://a.example/x", verdict_repository.VerdictDecision.ALLOWED, "ok"
        )
    )
    subject.record(
        verdict_repository.RecordVerdictRequest(
            "https://b.example/y", verdict_repository.VerdictDecision.DENIED, "blocked"
        )
    )
    listed = subject.all(verdict_repository.ListVerdictsRequest())

    assert [v.target_url for v in listed.verdicts] == [
        "https://a.example/x",
        "https://b.example/y",
    ]


def test_recording_the_same_url_twice_keeps_only_the_latest_verdict() -> None:
    subject = repo_memory.InMemoryVerdictRepository()

    subject.record(
        verdict_repository.RecordVerdictRequest(
            "https://ok.example/x", verdict_repository.VerdictDecision.ALLOWED, "ok"
        )
    )
    subject.record(
        verdict_repository.RecordVerdictRequest(
            "https://ok.example/x", verdict_repository.VerdictDecision.DENIED, "blocked"
        )
    )
    listed = subject.all(verdict_repository.ListVerdictsRequest())

    assert [(v.decision, v.reason) for v in listed.verdicts] == [
        (verdict_repository.VerdictDecision.DENIED, "blocked")
    ]


def test_record_fails_when_the_store_is_down() -> None:
    subject = repo_memory.InMemoryVerdictRepository(down=True)

    with pytest.raises(InfraError) as excinfo:
        subject.record(
            verdict_repository.RecordVerdictRequest(
                "https://ok.example/x", verdict_repository.VerdictDecision.ALLOWED, "ok"
            )
        )

    assert str(excinfo.value) == "linkpolicy store unavailable"


def test_all_fails_when_the_store_is_down() -> None:
    subject = repo_memory.InMemoryVerdictRepository(down=True)

    with pytest.raises(InfraError) as excinfo:
        subject.all(verdict_repository.ListVerdictsRequest())

    assert str(excinfo.value) == "linkpolicy store unavailable"


def test_closing_a_repository_does_not_discard_what_it_recorded() -> None:
    subject = repo_memory.InMemoryVerdictRepository()

    subject.record(
        verdict_repository.RecordVerdictRequest(
            "https://ok.example/x", verdict_repository.VerdictDecision.ALLOWED, "ok"
        )
    )
    subject.close()
    listed = subject.all(verdict_repository.ListVerdictsRequest())

    assert [v.target_url for v in listed.verdicts] == ["https://ok.example/x"]


def test_close_counts_every_call() -> None:
    subject = repo_memory.InMemoryVerdictRepository()

    subject.close()
    subject.close()

    assert subject.close_count == 2


def test_a_repository_starts_closed_zero_times() -> None:
    assert repo_memory.InMemoryVerdictRepository().close_count == 0
