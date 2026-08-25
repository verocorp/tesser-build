from __future__ import annotations

import pytest

import reports.domain.report as report
import tesser.errors as errors


def test_a_link_carries_its_slug_and_target_as_value_objects() -> None:
    link = report.Link(report.LinkSpec("spring-sale", "https://a.example/s"))
    assert str(link.slug) == "spring-sale"
    assert str(link.target_url) == "https://a.example/s"


def test_a_link_refuses_a_target_the_reader_cannot_follow() -> None:
    with pytest.raises(errors.DomainError):
        report.Link(report.LinkSpec("spring-sale", "not-a-url"))


def test_a_recorded_verdict_reads_its_flag_as_a_decision() -> None:
    allowed = report.RecordedVerdict(
        report.RecordedVerdictSpec("https://a.example/s", True, "on the allowlist")
    )
    denied = report.RecordedVerdict(
        report.RecordedVerdictSpec("https://a.example/s", False, "host blocked")
    )
    assert str(allowed.allowed) == "allowed"
    assert str(denied.allowed) == "denied"
    assert str(denied.reason) == "host blocked"


def test_a_recorded_verdict_refuses_an_empty_reason() -> None:
    with pytest.raises(errors.DomainError):
        report.RecordedVerdict(report.RecordedVerdictSpec("https://a.example/s", True, ""))


def test_a_link_verdict_carries_the_link_and_the_decision_together() -> None:
    row = report.LinkVerdict(
        report.LinkVerdictSpec("spring-sale", "https://a.example/s", False, "host blocked")
    )
    assert str(row.slug) == "spring-sale"
    assert str(row.target_url) == "https://a.example/s"
    assert str(row.allowed) == "denied"
    assert str(row.reason) == "host blocked"


def test_a_link_verdict_is_equal_by_value() -> None:
    first = report.LinkVerdict(
        report.LinkVerdictSpec("spring-sale", "https://a.example/s", True, "on the allowlist")
    )
    second = report.LinkVerdict(
        report.LinkVerdictSpec("spring-sale", "https://a.example/s", True, "on the allowlist")
    )
    assert first == second
