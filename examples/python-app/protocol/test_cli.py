from __future__ import annotations

import pytest

import protocol as protocol


def test_a_declared_argument_reads_back() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    cli_request = protocol.CliRequest(("100.00", "USD"))
    assert cli_request.arg(0, "budget_amount", usage) == "100.00"
    assert cli_request.arg(1, "currency", usage) == "USD"


def test_a_missing_argument_is_a_usage_error_carrying_the_usage() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    cli_request = protocol.CliRequest(("100.00",))
    with pytest.raises(protocol.UsageError) as caught:
        cli_request.arg(1, "currency", usage)
    assert str(caught.value) == f"missing argument <currency>\n{usage}"


def test_an_empty_argument_is_a_usage_error() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    cli_request = protocol.CliRequest(("", "USD"))
    with pytest.raises(protocol.UsageError) as caught:
        cli_request.arg(0, "budget_amount", usage)
    assert "missing argument <budget_amount>" in str(caught.value)


def test_no_arguments_at_all_is_a_usage_error() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    with pytest.raises(protocol.UsageError):
        protocol.CliRequest(()).arg(0, "budget_amount", usage)


def test_the_declared_argument_count_passes() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    protocol.CliRequest(("100.00", "USD")).no_extra_args(2, usage)
    protocol.CliRequest(("100.00",)).no_extra_args(2, usage)


def test_an_extra_argument_is_a_usage_error_carrying_the_usage() -> None:
    usage = "usage: create-campaign <budget_amount> <currency>"
    cli_request = protocol.CliRequest(("100.00", "USD", "surplus"))
    with pytest.raises(protocol.UsageError) as caught:
        cli_request.no_extra_args(2, usage)
    assert str(caught.value) == f"unexpected extra arguments\n{usage}"


def test_an_ok_response_is_exit_zero_on_stdout() -> None:
    cli_response = protocol.CliResponse.ok("created campaign c-1")
    assert cli_response.exit_code == 0
    assert cli_response.stdout == "created campaign c-1"
    assert cli_response.stderr == ""


def test_a_failure_response_carries_its_code_and_stderr() -> None:
    cli_response = protocol.CliResponse(2, stdout="", stderr="[bad_amount] budget must be positive")
    assert cli_response.exit_code == 2
    assert cli_response.stdout == ""
    assert cli_response.stderr == "[bad_amount] budget must be positive"
