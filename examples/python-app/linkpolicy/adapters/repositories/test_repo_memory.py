from __future__ import annotations

import pytest

import linkpolicy.adapters.repositories as repositories
import linkpolicy.application.ports as ports


def test_all_answers_nothing_before_anything_is_recorded() -> None:
    in_memory_verdict_repository = repositories.InMemoryVerdictRepository()

    list_verdicts_response = in_memory_verdict_repository.all(ports.ListVerdictsRequest())

    assert list_verdicts_response.verdicts == ()


def test_a_recorded_verdict_comes_back_from_all() -> None:
    in_memory_verdict_repository = repositories.InMemoryVerdictRepository()

    in_memory_verdict_repository.record(
        ports.RecordVerdictRequest("https://ok.example/x", ports.VerdictDecision.ALLOWED, "ok")
    )
    list_verdicts_response = in_memory_verdict_repository.all(ports.ListVerdictsRequest())

    assert [
        (v.target_url, v.decision, v.reason) for v in list_verdicts_response.verdicts
    ] == [("https://ok.example/x", ports.VerdictDecision.ALLOWED, "ok")]


def test_all_keeps_the_order_the_urls_were_first_recorded_in() -> None:
    in_memory_verdict_repository = repositories.InMemoryVerdictRepository()

    in_memory_verdict_repository.record(
        ports.RecordVerdictRequest("https://a.example/x", ports.VerdictDecision.ALLOWED, "ok")
    )
    in_memory_verdict_repository.record(
        ports.RecordVerdictRequest("https://b.example/y", ports.VerdictDecision.DENIED, "blocked")
    )
    list_verdicts_response = in_memory_verdict_repository.all(ports.ListVerdictsRequest())

    assert [v.target_url for v in list_verdicts_response.verdicts] == [
        "https://a.example/x",
        "https://b.example/y",
    ]


def test_recording_the_same_url_twice_keeps_only_the_latest_verdict() -> None:
    in_memory_verdict_repository = repositories.InMemoryVerdictRepository()

    in_memory_verdict_repository.record(
        ports.RecordVerdictRequest("https://ok.example/x", ports.VerdictDecision.ALLOWED, "ok")
    )
    in_memory_verdict_repository.record(
        ports.RecordVerdictRequest("https://ok.example/x", ports.VerdictDecision.DENIED, "blocked")
    )
    list_verdicts_response = in_memory_verdict_repository.all(ports.ListVerdictsRequest())

    assert [(v.decision, v.reason) for v in list_verdicts_response.verdicts] == [
        (ports.VerdictDecision.DENIED, "blocked")
    ]


def test_record_fails_when_the_store_is_down() -> None:
    in_memory_verdict_repository = repositories.InMemoryVerdictRepository(down=True)

    with pytest.raises(ports.StoreUnavailable) as excinfo:
        in_memory_verdict_repository.record(
            ports.RecordVerdictRequest("https://ok.example/x", ports.VerdictDecision.ALLOWED, "ok")
        )

    assert str(excinfo.value) == "linkpolicy store unavailable"


def test_all_fails_when_the_store_is_down() -> None:
    in_memory_verdict_repository = repositories.InMemoryVerdictRepository(down=True)

    with pytest.raises(ports.StoreUnavailable) as excinfo:
        in_memory_verdict_repository.all(ports.ListVerdictsRequest())

    assert str(excinfo.value) == "linkpolicy store unavailable"


def test_closing_a_repository_does_not_discard_what_it_recorded() -> None:
    in_memory_verdict_repository = repositories.InMemoryVerdictRepository()

    in_memory_verdict_repository.record(
        ports.RecordVerdictRequest("https://ok.example/x", ports.VerdictDecision.ALLOWED, "ok")
    )
    in_memory_verdict_repository.close()
    list_verdicts_response = in_memory_verdict_repository.all(ports.ListVerdictsRequest())

    assert [v.target_url for v in list_verdicts_response.verdicts] == ["https://ok.example/x"]


def test_close_counts_every_call() -> None:
    in_memory_verdict_repository = repositories.InMemoryVerdictRepository()

    in_memory_verdict_repository.close()
    in_memory_verdict_repository.close()

    assert in_memory_verdict_repository.close_count == 2


def test_a_repository_starts_closed_zero_times() -> None:
    assert repositories.InMemoryVerdictRepository().close_count == 0
