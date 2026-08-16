from __future__ import annotations

import pytest

from protocol.cli import CliRequest, CliResponse, UsageError


def test_an_argument_at_its_index_comes_back() -> None:
    request = CliRequest(args=("/repo", "--verbose"))
    assert request.arg(0, "repo-root", "usage: prog <repo-root>") == "/repo"
    assert request.arg(1, "flag", "usage: prog <repo-root>") == "--verbose"


def test_a_missing_argument_names_itself_and_carries_the_usage() -> None:
    with pytest.raises(UsageError) as raised:
        CliRequest(args=()).arg(0, "repo-root", "usage: prog <repo-root>")
    assert "missing argument <repo-root>" in str(raised.value)
    assert "usage: prog <repo-root>" in str(raised.value)


def test_an_empty_argument_is_a_missing_argument() -> None:
    with pytest.raises(UsageError) as raised:
        CliRequest(args=("",)).arg(0, "repo-root", "usage: prog <repo-root>")
    assert "missing argument <repo-root>" in str(raised.value)


def test_an_argument_past_the_end_is_a_missing_argument() -> None:
    with pytest.raises(UsageError):
        CliRequest(args=("/repo",)).arg(1, "second", "usage: prog <repo-root>")


def test_the_exact_argument_count_passes_the_extra_argument_gate() -> None:
    request = CliRequest(args=("/repo",))
    request.no_extra_args(1, "usage: prog")
    assert request.arg(0, "repo-root", "usage: prog") == "/repo"


def test_fewer_arguments_than_the_count_pass_the_extra_argument_gate() -> None:
    request = CliRequest(args=())
    request.no_extra_args(1, "usage: prog")
    assert request.args == ()


def test_an_extra_argument_is_rejected_with_the_usage() -> None:
    with pytest.raises(UsageError) as raised:
        CliRequest(args=("/repo", "extra")).no_extra_args(1, "usage: prog <repo-root>")
    assert "unexpected extra arguments" in str(raised.value)
    assert "usage: prog <repo-root>" in str(raised.value)


def test_ok_is_exit_zero_on_stdout_with_an_empty_stderr() -> None:
    response = CliResponse.ok("done")
    assert response.exit_code == 0
    assert response.stdout == "done"
    assert response.stderr == ""


def test_a_response_carries_the_exit_code_and_both_streams() -> None:
    response = CliResponse(2, stdout="", stderr="boom")
    assert response.exit_code == 2
    assert response.stdout == ""
    assert response.stderr == "boom"


def test_two_responses_with_the_same_fields_are_equal() -> None:
    assert CliResponse.ok("done") == CliResponse(0, stdout="done", stderr="")
    assert CliResponse.ok("done") != CliResponse(1, stdout="done", stderr="")


def test_a_request_holds_its_arguments_as_given() -> None:
    assert CliRequest(args=("a", "b")).args == ("a", "b")
    assert CliRequest(args=("a", "b")) == CliRequest(args=("a", "b"))
