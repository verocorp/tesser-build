from __future__ import annotations

import pytest
import tesser.testing as ts

import protocol
import repo.adapters.handlers as handlers
import repo.client as client


@ts.fake
class FakeClientScripted(client.RepoClient):

    def __init__(
        self,
        problems: tuple[str, ...] = (),
        counts: tuple[str, ...] = ("5", "2"),
        trees: tuple[str, ...] = ("appone",),
    ) -> None:
        self._problems = problems
        self._counts = counts
        self._trees = trees

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        return client.CheckResponse(problems=self._problems, counts=self._counts)

    def trees(self, trees_request: client.TreesRequest) -> client.TreesResponse:
        return client.TreesResponse(trees=self._trees)


def test_a_clean_check_exits_zero_with_the_summary_line() -> None:
    handler = handlers.Handler(FakeClientScripted())
    cli_response = handler.check(protocol.CliRequest(args=("/repo",)))
    assert cli_response.exit_code == 0
    assert cli_response.stdout == (
        "layout: 5 rows, 2 app trees — disk, declarations, and gates agree"
    )
    assert cli_response.stderr == ""


def test_problems_exit_one_on_stderr_with_the_layout_prefix() -> None:
    handler = handlers.Handler(FakeClientScripted(problems=("first thing", "second thing")))
    cli_response = handler.check(protocol.CliRequest(args=("/repo",)))
    assert cli_response.exit_code == 1
    assert cli_response.stdout == ""
    assert cli_response.stderr == "layout: first thing\nlayout: second thing"


def test_a_missing_root_argument_is_a_usage_error() -> None:
    handler = handlers.Handler(FakeClientScripted())
    with pytest.raises(protocol.UsageError):
        handler.check(protocol.CliRequest(args=()))


def test_an_empty_root_argument_is_a_usage_error() -> None:
    handler = handlers.Handler(FakeClientScripted())
    with pytest.raises(protocol.UsageError):
        handler.check(protocol.CliRequest(args=("",)))


def test_an_extra_argument_is_a_usage_error() -> None:
    handler = handlers.Handler(FakeClientScripted())
    with pytest.raises(protocol.UsageError):
        handler.check(protocol.CliRequest(args=("/repo", "extra")))


def test_trees_prints_one_tree_per_line() -> None:
    handler = handlers.Handler(FakeClientScripted(trees=("appone", "libby")))
    cli_response = handler.trees(protocol.CliRequest(args=("/repo",)))
    assert cli_response.exit_code == 0
    assert cli_response.stdout == "appone\nlibby"
