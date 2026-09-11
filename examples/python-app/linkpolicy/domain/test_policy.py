from __future__ import annotations

import pytest

import linkpolicy.domain as domain
import tesser.errors as errors


def test_scheme_rejects_a_non_alphabetic_value() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.Scheme("ht2p")

    assert excinfo.value.code == "invalid_scheme"
    assert excinfo.value.message == "scheme 'ht2p' must be alphabetic"


def test_scheme_round_trips_through_its_canonical_exit() -> None:
    scheme = domain.Scheme("https")

    assert domain.Scheme(str(scheme)) == scheme


def test_host_rejects_an_empty_value() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.Host("")

    assert excinfo.value.code == "invalid_host"
    assert excinfo.value.message == "host must not be empty"


def test_target_url_rejects_an_empty_value() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.TargetURL("")

    assert excinfo.value.code == "invalid_target_url"
    assert excinfo.value.message == "target url must not be empty"


def test_reason_rejects_an_empty_value() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.Reason("")

    assert excinfo.value.code == "invalid_reason"
    assert excinfo.value.message == "reason must not be empty"


def test_decision_rejects_a_value_outside_its_taxonomy() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.Decision("maybe")

    assert excinfo.value.code == "invalid_decision"
    assert excinfo.value.message == "decision 'maybe' must be allowed or denied"


def test_verdict_exposes_its_parts_as_value_objects() -> None:
    verdict = domain.Verdict(domain.VerdictSpec("https://ok.example/x", True, "ok"))

    assert verdict.target_url == domain.TargetURL("https://ok.example/x")
    assert verdict.allowed == domain.Decision("allowed")
    assert verdict.reason == domain.Reason("ok")


def test_a_verdict_built_from_a_false_flag_is_denied() -> None:
    verdict = domain.Verdict(domain.VerdictSpec("https://ok.example/x", False, "blocked"))

    assert verdict.allowed == domain.Decision("denied")


def test_verdicts_built_from_the_same_parts_are_equal() -> None:
    one = domain.Verdict(domain.VerdictSpec("https://ok.example/x", True, "ok"))
    other = domain.Verdict(domain.VerdictSpec("https://ok.example/x", True, "ok"))

    assert one == other
    assert hash(one) == hash(other)


def test_verdicts_that_differ_in_decision_are_not_equal() -> None:
    allowed = domain.Verdict(domain.VerdictSpec("https://ok.example/x", True, "ok"))
    denied = domain.Verdict(domain.VerdictSpec("https://ok.example/x", False, "ok"))

    assert allowed != denied


def test_verdict_rejects_an_empty_reason() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.Verdict(domain.VerdictSpec("https://ok.example/x", True, ""))

    assert excinfo.value.code == "invalid_reason"


def test_verdict_rejects_an_empty_target_url() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.Verdict(domain.VerdictSpec("", True, "ok"))

    assert excinfo.value.code == "invalid_target_url"


def test_policy_exposes_the_schemes_and_hosts_it_was_given() -> None:
    policy = domain.Policy(domain.PolicySpec(("https", "ftp"), ("bad.example",)))

    assert policy.allowed_schemes == (domain.Scheme("https"), domain.Scheme("ftp"))
    assert policy.blocked_hosts == (domain.Host("bad.example"),)


def test_policy_rejects_a_non_alphabetic_scheme_at_construction() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.Policy(domain.PolicySpec(("ht2p",), ()))

    assert excinfo.value.code == "invalid_scheme"


def test_policy_rejects_an_empty_blocked_host_at_construction() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        domain.Policy(domain.PolicySpec(("https",), ("",)))

    assert excinfo.value.code == "invalid_host"


def test_evaluate_allows_a_url_the_policy_permits() -> None:
    policy = domain.Policy(domain.PolicySpec(("https",), ("bad.example",)))

    verdict = policy.evaluate(domain.TargetURL("https://ok.example/x"))

    assert verdict.target_url == domain.TargetURL("https://ok.example/x")
    assert verdict.allowed == domain.Decision("allowed")
    assert verdict.reason == domain.Reason("ok")


def test_evaluate_denies_a_scheme_outside_the_allowed_set() -> None:
    policy = domain.Policy(domain.PolicySpec(("https",), ()))

    verdict = policy.evaluate(domain.TargetURL("http://ok.example/x"))

    assert verdict.allowed == domain.Decision("denied")
    assert verdict.reason == domain.Reason("scheme 'http' not allowed")


def test_evaluate_denies_a_url_that_carries_no_scheme() -> None:
    policy = domain.Policy(domain.PolicySpec(("https",), ()))

    verdict = policy.evaluate(domain.TargetURL("ok.example/x"))

    assert verdict.allowed == domain.Decision("denied")
    assert verdict.reason == domain.Reason("scheme '(none)' not allowed")


def test_evaluate_denies_a_blocked_host() -> None:
    policy = domain.Policy(domain.PolicySpec(("https",), ("bad.example",)))

    verdict = policy.evaluate(domain.TargetURL("https://bad.example/x"))

    assert verdict.allowed == domain.Decision("denied")
    assert verdict.reason == domain.Reason("host 'bad.example' is blocked")


def test_evaluate_matches_a_blocked_host_regardless_of_case() -> None:
    policy = domain.Policy(domain.PolicySpec(("https",), ("bad.example",)))

    verdict = policy.evaluate(domain.TargetURL("https://BAD.example/x"))

    assert verdict.reason == domain.Reason("host 'bad.example' is blocked")


def test_evaluate_matches_a_blocked_host_regardless_of_port() -> None:
    policy = domain.Policy(domain.PolicySpec(("https",), ("bad.example",)))

    verdict = policy.evaluate(domain.TargetURL("https://bad.example:8443/x"))

    assert verdict.reason == domain.Reason("host 'bad.example' is blocked")


def test_evaluate_reports_the_scheme_before_the_host() -> None:
    policy = domain.Policy(domain.PolicySpec(("https",), ("bad.example",)))

    verdict = policy.evaluate(domain.TargetURL("http://bad.example/x"))

    assert verdict.reason == domain.Reason("scheme 'http' not allowed")


def test_evaluate_keeps_the_url_it_was_asked_about_on_a_denial() -> None:
    policy = domain.Policy(domain.PolicySpec(("https",), ()))

    verdict = policy.evaluate(domain.TargetURL("http://ok.example/x"))

    assert verdict.target_url == domain.TargetURL("http://ok.example/x")


def test_the_default_policy_allows_https_and_blocks_the_known_bad_hosts() -> None:
    policy = domain.Policy(domain.PolicySpec())

    assert policy.allowed_schemes == (domain.Scheme("https"),)
    assert policy.blocked_hosts == (
        domain.Host("evil.example"),
        domain.Host("malware.test"),
    )
