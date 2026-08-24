from __future__ import annotations

import pytest

import reports.domain.values as values
import tesser.errors as errors


def test_a_target_url_accepts_an_http_and_an_https_target() -> None:
    assert str(values.TargetURL("http://a.example/x")) == "http://a.example/x"
    assert str(values.TargetURL("https://a.example/x")) == "https://a.example/x"


def test_a_target_url_rejects_a_scheme_the_reader_cannot_follow() -> None:
    with pytest.raises(errors.DomainError):
        values.TargetURL("ftp://a.example/x")


def test_a_target_url_rejects_an_embedded_space() -> None:
    with pytest.raises(errors.DomainError):
        values.TargetURL("https://a.example/a b")


def test_a_target_url_rejects_the_empty_string() -> None:
    with pytest.raises(errors.DomainError):
        values.TargetURL("")


def test_a_target_url_is_equal_by_value() -> None:
    assert values.TargetURL("https://a.example/x") == values.TargetURL("https://a.example/x")
    assert values.TargetURL("https://a.example/x") != values.TargetURL("https://a.example/y")


def test_a_target_url_hashes_with_its_value() -> None:
    first = values.TargetURL("https://a.example/x")
    second = values.TargetURL("https://a.example/x")
    assert hash(first) == hash(second)
    assert len({first, second}) == 1


def test_a_target_url_round_trips_through_its_canonical_exit() -> None:
    url = values.TargetURL("https://a.example/x")
    assert values.TargetURL(str(url)) == url


def test_a_decision_admits_exactly_two_words() -> None:
    assert str(values.Decision("allowed")) == "allowed"
    assert str(values.Decision("denied")) == "denied"


def test_a_decision_rejects_a_word_outside_its_closed_set() -> None:
    with pytest.raises(errors.DomainError):
        values.Decision("maybe")


def test_a_decision_is_equal_by_value() -> None:
    assert values.Decision("allowed") == values.Decision("allowed")
    assert values.Decision("allowed") != values.Decision("denied")


def test_a_decision_round_trips_through_its_canonical_exit() -> None:
    decision = values.Decision("denied")
    assert values.Decision(str(decision)) == decision


def test_a_reason_rejects_the_empty_string() -> None:
    with pytest.raises(errors.DomainError):
        values.Reason("")


def test_a_reason_is_equal_by_value() -> None:
    assert values.Reason("host blocked") == values.Reason("host blocked")
    assert values.Reason("host blocked") != values.Reason("no verdict recorded")


def test_a_reason_round_trips_through_its_canonical_exit() -> None:
    reason = values.Reason("host blocked")
    assert values.Reason(str(reason)) == reason


def test_two_different_value_types_carrying_one_word_are_not_equal() -> None:
    assert values.Decision("allowed") != values.Reason("allowed")
