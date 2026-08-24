from __future__ import annotations

import pytest

import protocol.cli as cli


def test_a_declared_argument_reads_back() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    req = cli.CliRequest(("100.00", "USD"))
    assert req.arg(0, "budget_amount", usage) == "100.00"
    assert req.arg(1, "currency", usage) == "USD"


def test_a_missing_argument_is_a_usage_error_carrying_the_usage() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    req = cli.CliRequest(("100.00",))
    with pytest.raises(cli.UsageError) as caught:
        req.arg(1, "currency", usage)
    assert str(caught.value) == f"missing argument <currency>\n{usage}"


def test_an_empty_argument_is_a_usage_error() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    req = cli.CliRequest(("", "USD"))
    with pytest.raises(cli.UsageError) as caught:
        req.arg(0, "budget_amount", usage)
    assert "missing argument <budget_amount>" in str(caught.value)


def test_no_arguments_at_all_is_a_usage_error() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    with pytest.raises(cli.UsageError):
        cli.CliRequest(()).arg(0, "budget_amount", usage)


def test_the_declared_argument_count_passes() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    cli.CliRequest(("100.00", "USD")).no_extra_args(2, usage)
    cli.CliRequest(("100.00",)).no_extra_args(2, usage)


def test_an_extra_argument_is_a_usage_error_carrying_the_usage() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    req = cli.CliRequest(("100.00", "USD", "surplus"))
    with pytest.raises(cli.UsageError) as caught:
        req.no_extra_args(2, usage)
    assert str(caught.value) == f"unexpected extra arguments\n{usage}"


def test_an_ok_response_is_exit_zero_on_stdout() -> None:
    resp = cli.CliResponse.ok("created campaign c-1")
    assert resp.exit_code == 0
    assert resp.stdout == "created campaign c-1"
    assert resp.stderr == ""


def test_a_failure_response_carries_its_code_and_stderr() -> None:
    resp = cli.CliResponse(2, stdout="", stderr="[bad_amount] budget must be positive")
    assert resp.exit_code == 2
    assert resp.stdout == ""
    assert resp.stderr == "[bad_amount] budget must be positive"
