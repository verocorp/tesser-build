from __future__ import annotations

import pytest
import tesser.testing as ts

import reports.domain as domain
import tesser.errors as errors


@ts.helper
def _link_verdicts_spec(
    slug: str = "spring-sale",
    target_url: str = "https://a.example/s",
    decision: str = "denied",
    reason: str = "host blocked",
) -> domain.LinkVerdictsSpec:
    return domain.LinkVerdictsSpec(
        links=(domain.LinkSpec(slug, target_url),),
        verdicts=(domain.RecordedVerdictSpec(target_url, decision, reason),),
    )


def test_a_link_carries_its_slug_and_target_as_value_objects() -> None:
    link = domain.Link(domain.LinkSpec("spring-sale", "https://a.example/s"))
    assert str(link.slug) == "spring-sale"
    assert str(link.target_url) == "https://a.example/s"


def test_a_link_refuses_a_target_the_reader_cannot_follow() -> None:
    with pytest.raises(errors.DomainError):
        domain.Link(domain.LinkSpec("spring-sale", "not-a-url"))


def test_a_recorded_verdict_carries_its_decision_as_a_value_object() -> None:
    allowed = domain.RecordedVerdict(
        domain.RecordedVerdictSpec("https://a.example/s", "allowed", "on the allowlist")
    )
    denied = domain.RecordedVerdict(
        domain.RecordedVerdictSpec("https://a.example/s", "denied", "host blocked")
    )
    assert str(allowed.decision) == "allowed"
    assert str(denied.decision) == "denied"
    assert str(denied.reason) == "host blocked"


def test_a_recorded_verdict_refuses_a_decision_outside_the_set() -> None:
    with pytest.raises(errors.DomainError):
        domain.RecordedVerdict(
            domain.RecordedVerdictSpec("https://a.example/s", "maybe", "unsure")
        )


def test_a_recorded_verdict_refuses_an_empty_reason() -> None:
    with pytest.raises(errors.DomainError):
        domain.RecordedVerdict(
            domain.RecordedVerdictSpec("https://a.example/s", "allowed", "")
        )


def test_a_link_verdict_carries_the_link_and_the_decision_together() -> None:
    link_verdict = domain.LinkVerdict(
        domain.LinkVerdictSpec("spring-sale", "https://a.example/s", "denied", "host blocked")
    )
    assert str(link_verdict.slug) == "spring-sale"
    assert str(link_verdict.target_url) == "https://a.example/s"
    assert str(link_verdict.decision) == "denied"
    assert str(link_verdict.reason) == "host blocked"


def test_a_link_verdict_is_equal_by_value() -> None:
    first = domain.LinkVerdict(
        domain.LinkVerdictSpec("spring-sale", "https://a.example/s", "allowed", "on the allowlist")
    )
    second = domain.LinkVerdict(
        domain.LinkVerdictSpec("spring-sale", "https://a.example/s", "allowed", "on the allowlist")
    )
    assert first == second


def test_a_link_is_joined_to_the_verdict_recorded_for_its_target() -> None:
    link_verdicts = domain.LinkVerdicts(
        domain.LinkVerdictsSpec(
            links=(domain.LinkSpec("spring-sale", "https://a.example/s"),),
            verdicts=(
                domain.RecordedVerdictSpec("https://a.example/s", "denied", "host blocked"),
            ),
        )
    )
    assert link_verdicts.rows == (
        domain.LinkVerdict(
            domain.LinkVerdictSpec(
                "spring-sale", "https://a.example/s", "denied", "host blocked"
            )
        ),
    )


def test_a_link_nobody_ruled_on_is_allowed_and_says_so() -> None:
    link_verdicts = domain.LinkVerdicts(
        domain.LinkVerdictsSpec(
            links=(domain.LinkSpec("spring-sale", "https://a.example/s"),), verdicts=()
        )
    )
    assert str(link_verdicts.rows[0].decision) == "allowed"
    assert str(link_verdicts.rows[0].reason) == "no verdict recorded"


def test_a_verdict_for_a_target_nobody_links_to_is_left_out() -> None:
    link_verdicts = domain.LinkVerdicts(
        domain.LinkVerdictsSpec(
            links=(),
            verdicts=(
                domain.RecordedVerdictSpec("https://a.example/o", "denied", "host blocked"),
            ),
        )
    )
    assert link_verdicts.rows == ()


def test_a_denied_link_is_ordered_ahead_of_an_allowed_one() -> None:
    link_verdicts = domain.LinkVerdicts(
        domain.LinkVerdictsSpec(
            links=(
                domain.LinkSpec("allowed-one", "https://a.example/a"),
                domain.LinkSpec("denied-one", "https://a.example/d"),
            ),
            verdicts=(
                domain.RecordedVerdictSpec("https://a.example/d", "denied", "host blocked"),
            ),
        )
    )
    assert [str(row.slug) for row in link_verdicts.rows] == ["denied-one", "allowed-one"]


def test_links_sharing_a_decision_are_ordered_by_slug() -> None:
    link_verdicts = domain.LinkVerdicts(
        domain.LinkVerdictsSpec(
            links=(
                domain.LinkSpec("b-link", "https://a.example/b"),
                domain.LinkSpec("a-link", "https://a.example/a"),
            ),
            verdicts=(),
        )
    )
    assert [str(row.slug) for row in link_verdicts.rows] == ["a-link", "b-link"]


def test_the_last_verdict_recorded_for_a_target_is_the_one_reported() -> None:
    link_verdicts = domain.LinkVerdicts(
        domain.LinkVerdictsSpec(
            links=(domain.LinkSpec("spring-sale", "https://a.example/s"),),
            verdicts=(
                domain.RecordedVerdictSpec("https://a.example/s", "allowed", "first"),
                domain.RecordedVerdictSpec("https://a.example/s", "denied", "second"),
            ),
        )
    )
    assert str(link_verdicts.rows[0].decision) == "denied"
    assert str(link_verdicts.rows[0].reason) == "second"


def test_a_verdict_the_domain_would_not_accept_fails_the_whole_join() -> None:
    with pytest.raises(errors.DomainError):
        domain.LinkVerdicts(
            domain.LinkVerdictsSpec(
                links=(),
                verdicts=(domain.RecordedVerdictSpec("https://a.example/s", "allowed", ""),),
            )
        )


def test_two_joins_of_the_same_links_and_verdicts_are_equal() -> None:
    link_verdicts = domain.LinkVerdicts(
        domain.LinkVerdictsSpec(
            links=(domain.LinkSpec("spring-sale", "https://a.example/s"),), verdicts=()
        )
    )

    assert domain.LinkVerdicts(_link_verdicts_spec()) == domain.LinkVerdicts(
        _link_verdicts_spec()
    )
    assert domain.LinkVerdicts(_link_verdicts_spec()) != link_verdicts


def test_a_target_url_accepts_an_http_and_an_https_target() -> None:
    assert str(domain.TargetURL("http://a.example/x")) == "http://a.example/x"
    assert str(domain.TargetURL("https://a.example/x")) == "https://a.example/x"


def test_a_target_url_rejects_a_scheme_the_reader_cannot_follow() -> None:
    with pytest.raises(errors.DomainError):
        domain.TargetURL("ftp://a.example/x")


def test_a_target_url_rejects_an_embedded_space() -> None:
    with pytest.raises(errors.DomainError):
        domain.TargetURL("https://a.example/a b")


def test_a_target_url_rejects_the_empty_string() -> None:
    with pytest.raises(errors.DomainError):
        domain.TargetURL("")


def test_a_target_url_is_equal_by_value() -> None:
    assert domain.TargetURL("https://a.example/x") == domain.TargetURL("https://a.example/x")
    assert domain.TargetURL("https://a.example/x") != domain.TargetURL("https://a.example/y")


def test_a_target_url_hashes_with_its_value() -> None:
    first = domain.TargetURL("https://a.example/x")
    second = domain.TargetURL("https://a.example/x")
    assert hash(first) == hash(second)
    assert len({first, second}) == 1


def test_a_target_url_round_trips_through_its_canonical_exit() -> None:
    target_url = domain.TargetURL("https://a.example/x")
    assert domain.TargetURL(str(target_url)) == target_url


def test_a_decision_admits_exactly_two_words() -> None:
    assert str(domain.Decision("allowed")) == "allowed"
    assert str(domain.Decision("denied")) == "denied"


def test_a_decision_rejects_a_word_outside_its_closed_set() -> None:
    with pytest.raises(errors.DomainError):
        domain.Decision("maybe")


def test_a_decision_is_equal_by_value() -> None:
    assert domain.Decision("allowed") == domain.Decision("allowed")
    assert domain.Decision("allowed") != domain.Decision("denied")


def test_a_decision_round_trips_through_its_canonical_exit() -> None:
    decision = domain.Decision("denied")
    assert domain.Decision(str(decision)) == decision


def test_a_reason_rejects_the_empty_string() -> None:
    with pytest.raises(errors.DomainError):
        domain.Reason("")


def test_a_reason_is_equal_by_value() -> None:
    assert domain.Reason("host blocked") == domain.Reason("host blocked")
    assert domain.Reason("host blocked") != domain.Reason("no verdict recorded")


def test_a_reason_round_trips_through_its_canonical_exit() -> None:
    reason = domain.Reason("host blocked")
    assert domain.Reason(str(reason)) == reason


def test_two_different_value_types_carrying_one_word_are_not_equal() -> None:
    assert domain.Decision("allowed") != domain.Reason("allowed")
