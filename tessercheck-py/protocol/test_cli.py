from __future__ import annotations

import pytest

import protocol


def test_a_missing_positional_argument_falls_back_to_the_default() -> None:
    assert protocol.CliRequest(args=()).arg(0, ".") == "."
    assert protocol.CliRequest(args=("tree",)).arg(1, "--none") == "--none"


def test_a_present_positional_argument_wins_over_the_default() -> None:
    cli_request = protocol.CliRequest(args=("some/tree", "second"))
    assert cli_request.arg(0, ".") == "some/tree"
    assert cli_request.arg(1, ".") == "second"


def test_the_expected_number_of_arguments_is_accepted_silently() -> None:
    protocol.CliRequest(args=()).no_extra_args(1, "usage: check [tree]")
    protocol.CliRequest(args=("tree",)).no_extra_args(1, "usage: check [tree]")


def test_a_surplus_argument_is_a_usage_error_carrying_the_usage_line() -> None:
    with pytest.raises(protocol.UsageError) as caught:
        protocol.CliRequest(args=("tree", "surplus")).no_extra_args(1, "usage: check [tree]")
    assert "unexpected extra arguments" in str(caught.value)
    assert "usage: check [tree]" in str(caught.value)


def test_a_request_that_takes_no_arguments_rejects_the_first_one() -> None:
    with pytest.raises(protocol.UsageError):
        protocol.CliRequest(args=("tree",)).no_extra_args(0, "usage: rules")


def test_a_response_carries_the_exit_code_and_both_streams() -> None:
    cli_response = protocol.CliResponse(2, stdout="out", stderr="err")
    assert cli_response.exit_code == 2
    assert cli_response.stdout == "out"
    assert cli_response.stderr == "err"
