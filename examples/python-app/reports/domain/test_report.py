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


def test_a_recorded_verdict_carries_its_decision_as_a_value_object() -> None:
    allowed = report.RecordedVerdict(
        report.RecordedVerdictSpec("https://a.example/s", "allowed", "on the allowlist")
    )
    denied = report.RecordedVerdict(
        report.RecordedVerdictSpec("https://a.example/s", "denied", "host blocked")
    )
    assert str(allowed.decision) == "allowed"
    assert str(denied.decision) == "denied"
    assert str(denied.reason) == "host blocked"


def test_a_recorded_verdict_refuses_a_decision_outside_the_set() -> None:
    with pytest.raises(errors.DomainError):
        report.RecordedVerdict(
            report.RecordedVerdictSpec("https://a.example/s", "maybe", "unsure")
        )


def test_a_recorded_verdict_refuses_an_empty_reason() -> None:
    with pytest.raises(errors.DomainError):
        report.RecordedVerdict(
            report.RecordedVerdictSpec("https://a.example/s", "allowed", "")
        )


def test_a_link_verdict_carries_the_link_and_the_decision_together() -> None:
    row = report.LinkVerdict(
        report.LinkVerdictSpec("spring-sale", "https://a.example/s", "denied", "host blocked")
    )
    assert str(row.slug) == "spring-sale"
    assert str(row.target_url) == "https://a.example/s"
    assert str(row.decision) == "denied"
    assert str(row.reason) == "host blocked"


def test_a_link_verdict_is_equal_by_value() -> None:
    first = report.LinkVerdict(
        report.LinkVerdictSpec("spring-sale", "https://a.example/s", "allowed", "on the allowlist")
    )
    second = report.LinkVerdict(
        report.LinkVerdictSpec("spring-sale", "https://a.example/s", "allowed", "on the allowlist")
    )
    assert first == second


def test_a_link_is_joined_to_the_verdict_recorded_for_its_target() -> None:
    joined = report.LinkVerdicts(
        report.LinkVerdictsSpec(
            links=(report.LinkSpec("spring-sale", "https://a.example/s"),),
            verdicts=(
                report.RecordedVerdictSpec("https://a.example/s", "denied", "host blocked"),
            ),
        )
    )
    assert joined.rows == (
        report.LinkVerdict(
            report.LinkVerdictSpec(
                "spring-sale", "https://a.example/s", "denied", "host blocked"
            )
        ),
    )


def test_a_link_nobody_ruled_on_is_allowed_and_says_so() -> None:
    joined = report.LinkVerdicts(
        report.LinkVerdictsSpec(
            links=(report.LinkSpec("spring-sale", "https://a.example/s"),), verdicts=()
        )
    )
    assert str(joined.rows[0].decision) == "allowed"
    assert str(joined.rows[0].reason) == "no verdict recorded"


def test_a_verdict_for_a_target_nobody_links_to_is_left_out() -> None:
    joined = report.LinkVerdicts(
        report.LinkVerdictsSpec(
            links=(),
            verdicts=(
                report.RecordedVerdictSpec("https://a.example/o", "denied", "host blocked"),
            ),
        )
    )
    assert joined.rows == ()


def test_a_denied_link_is_ordered_ahead_of_an_allowed_one() -> None:
    joined = report.LinkVerdicts(
        report.LinkVerdictsSpec(
            links=(
                report.LinkSpec("allowed-one", "https://a.example/a"),
                report.LinkSpec("denied-one", "https://a.example/d"),
            ),
            verdicts=(
                report.RecordedVerdictSpec("https://a.example/d", "denied", "host blocked"),
            ),
        )
    )
    assert [str(row.slug) for row in joined.rows] == ["denied-one", "allowed-one"]


def test_links_sharing_a_decision_are_ordered_by_slug() -> None:
    joined = report.LinkVerdicts(
        report.LinkVerdictsSpec(
            links=(
                report.LinkSpec("b-link", "https://a.example/b"),
                report.LinkSpec("a-link", "https://a.example/a"),
            ),
            verdicts=(),
        )
    )
    assert [str(row.slug) for row in joined.rows] == ["a-link", "b-link"]


def test_the_last_verdict_recorded_for_a_target_is_the_one_reported() -> None:
    joined = report.LinkVerdicts(
        report.LinkVerdictsSpec(
            links=(report.LinkSpec("spring-sale", "https://a.example/s"),),
            verdicts=(
                report.RecordedVerdictSpec("https://a.example/s", "allowed", "first"),
                report.RecordedVerdictSpec("https://a.example/s", "denied", "second"),
            ),
        )
    )
    assert str(joined.rows[0].decision) == "denied"
    assert str(joined.rows[0].reason) == "second"


def test_a_verdict_the_domain_would_not_accept_fails_the_whole_join() -> None:
    with pytest.raises(errors.DomainError):
        report.LinkVerdicts(
            report.LinkVerdictsSpec(
                links=(),
                verdicts=(report.RecordedVerdictSpec("https://a.example/s", "allowed", ""),),
            )
        )


def test_two_joins_of_the_same_links_and_verdicts_are_equal() -> None:
    def joined() -> report.LinkVerdicts:
        return report.LinkVerdicts(
            report.LinkVerdictsSpec(
                links=(report.LinkSpec("spring-sale", "https://a.example/s"),),
                verdicts=(
                    report.RecordedVerdictSpec("https://a.example/s", "denied", "host blocked"),
                ),
            )
        )

    other = report.LinkVerdicts(
        report.LinkVerdictsSpec(
            links=(report.LinkSpec("spring-sale", "https://a.example/s"),), verdicts=()
        )
    )

    assert joined() == joined()
    assert joined() != other
