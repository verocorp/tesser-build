from __future__ import annotations

import pytest

import linkpolicy.domain.policy as policy
from tesser.errors import DomainError


def test_scheme_rejects_a_non_alphabetic_value() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.Scheme("ht2p")

    assert excinfo.value.code == "invalid_scheme"
    assert excinfo.value.message == "scheme 'ht2p' must be alphabetic"


def test_scheme_round_trips_through_its_canonical_exit() -> None:
    scheme = policy.Scheme("https")

    assert policy.Scheme(str(scheme)) == scheme


def test_host_rejects_an_empty_value() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.Host("")

    assert excinfo.value.code == "invalid_host"
    assert excinfo.value.message == "host must not be empty"


def test_target_url_rejects_an_empty_value() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.TargetURL("")

    assert excinfo.value.code == "invalid_target_url"
    assert excinfo.value.message == "target url must not be empty"


def test_reason_rejects_an_empty_value() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.Reason("")

    assert excinfo.value.code == "invalid_reason"
    assert excinfo.value.message == "reason must not be empty"


def test_decision_rejects_a_value_outside_its_taxonomy() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.Decision("maybe")

    assert excinfo.value.code == "invalid_decision"
    assert excinfo.value.message == "decision 'maybe' must be allowed or denied"


def test_verdict_exposes_its_parts_as_value_objects() -> None:
    verdict = policy.Verdict("https://ok.example/x", True, "ok")

    assert verdict.target_url == policy.TargetURL("https://ok.example/x")
    assert verdict.allowed == policy.Decision("allowed")
    assert verdict.reason == policy.Reason("ok")


def test_a_verdict_built_from_a_false_flag_is_denied() -> None:
    verdict = policy.Verdict("https://ok.example/x", False, "blocked")

    assert verdict.allowed == policy.Decision("denied")


def test_verdicts_built_from_the_same_parts_are_equal() -> None:
    one = policy.Verdict("https://ok.example/x", True, "ok")
    other = policy.Verdict("https://ok.example/x", True, "ok")

    assert one == other
    assert hash(one) == hash(other)


def test_verdicts_that_differ_in_decision_are_not_equal() -> None:
    allowed = policy.Verdict("https://ok.example/x", True, "ok")
    denied = policy.Verdict("https://ok.example/x", False, "ok")

    assert allowed != denied


def test_verdict_rejects_an_empty_reason() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.Verdict("https://ok.example/x", True, "")

    assert excinfo.value.code == "invalid_reason"


def test_verdict_rejects_an_empty_target_url() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.Verdict("", True, "ok")

    assert excinfo.value.code == "invalid_target_url"


def test_policy_exposes_the_schemes_and_hosts_it_was_given() -> None:
    subject = policy.Policy(("https", "ftp"), ("bad.example",))

    assert subject.allowed_schemes == (policy.Scheme("https"), policy.Scheme("ftp"))
    assert subject.blocked_hosts == (policy.Host("bad.example"),)


def test_policy_rejects_a_non_alphabetic_scheme_at_construction() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.Policy(("ht2p",), ())

    assert excinfo.value.code == "invalid_scheme"


def test_policy_rejects_an_empty_blocked_host_at_construction() -> None:
    with pytest.raises(DomainError) as excinfo:
        policy.Policy(("https",), ("",))

    assert excinfo.value.code == "invalid_host"


def test_evaluate_allows_a_url_the_policy_permits() -> None:
    verdict = policy.Policy(("https",), ("bad.example",)).evaluate("https://ok.example/x")

    assert verdict.target_url == policy.TargetURL("https://ok.example/x")
    assert verdict.allowed == policy.Decision("allowed")
    assert verdict.reason == policy.Reason("ok")


def test_evaluate_denies_a_scheme_outside_the_allowed_set() -> None:
    verdict = policy.Policy(("https",), ()).evaluate("http://ok.example/x")

    assert verdict.allowed == policy.Decision("denied")
    assert verdict.reason == policy.Reason("scheme 'http' not allowed")


def test_evaluate_denies_a_url_that_carries_no_scheme() -> None:
    verdict = policy.Policy(("https",), ()).evaluate("ok.example/x")

    assert verdict.allowed == policy.Decision("denied")
    assert verdict.reason == policy.Reason("scheme '(none)' not allowed")


def test_evaluate_denies_a_blocked_host() -> None:
    verdict = policy.Policy(("https",), ("bad.example",)).evaluate("https://bad.example/x")

    assert verdict.allowed == policy.Decision("denied")
    assert verdict.reason == policy.Reason("host 'bad.example' is blocked")


def test_evaluate_matches_a_blocked_host_regardless_of_case() -> None:
    verdict = policy.Policy(("https",), ("bad.example",)).evaluate("https://BAD.example/x")

    assert verdict.reason == policy.Reason("host 'bad.example' is blocked")


def test_evaluate_matches_a_blocked_host_regardless_of_port() -> None:
    verdict = policy.Policy(("https",), ("bad.example",)).evaluate("https://bad.example:8443/x")

    assert verdict.reason == policy.Reason("host 'bad.example' is blocked")


def test_evaluate_reports_the_scheme_before_the_host() -> None:
    verdict = policy.Policy(("https",), ("bad.example",)).evaluate("http://bad.example/x")

    assert verdict.reason == policy.Reason("scheme 'http' not allowed")


def test_evaluate_keeps_the_url_it_was_asked_about_on_a_denial() -> None:
    verdict = policy.Policy(("https",), ()).evaluate("http://ok.example/x")

    assert verdict.target_url == policy.TargetURL("http://ok.example/x")


def test_the_default_policy_allows_https_and_blocks_the_known_bad_hosts() -> None:
    subject = policy.Policy()

    assert subject.allowed_schemes == (policy.Scheme("https"),)
    assert subject.blocked_hosts == (
        policy.Host("evil.example"),
        policy.Host("malware.test"),
    )
