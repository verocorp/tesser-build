from __future__ import annotations

import tesser.testing as ts

import repo.adapters.handlers.cli as cli
import repo.client.client as client
from protocol.cli import CliRequest, UsageError

import pytest


@ts.fake
class FakeClientScripted(client.Client):
    def __init__(
        self,
        problems: tuple[str, ...] = (),
        counts: tuple[str, ...] = ("5", "2"),
        trees: tuple[str, ...] = ("appone",),
    ) -> None:
        self._problems = problems
        self._counts = counts
        self._trees = trees

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        return client.CheckResponse(problems=self._problems, counts=self._counts)

    def trees(self, request: client.TreesRequest) -> client.TreesResponse:
        return client.TreesResponse(trees=self._trees)


def test_a_clean_check_exits_zero_with_the_summary_line() -> None:
    handler = cli.Handler(FakeClientScripted())
    response = handler.check(CliRequest(args=("/repo",)))
    assert response.exit_code == 0
    assert response.stdout == (
        "layout: 5 rows, 2 app trees — disk, declarations, and gates agree"
    )
    assert response.stderr == ""


def test_problems_exit_one_on_stderr_with_the_layout_prefix() -> None:
    handler = cli.Handler(FakeClientScripted(problems=("first thing", "second thing")))
    response = handler.check(CliRequest(args=("/repo",)))
    assert response.exit_code == 1
    assert response.stdout == ""
    assert response.stderr == "layout: first thing\nlayout: second thing"


def test_a_missing_root_argument_is_a_usage_error() -> None:
    handler = cli.Handler(FakeClientScripted())
    with pytest.raises(UsageError):
        handler.check(CliRequest(args=()))


def test_an_empty_root_argument_is_a_usage_error() -> None:
    handler = cli.Handler(FakeClientScripted())
    with pytest.raises(UsageError):
        handler.check(CliRequest(args=("",)))


def test_an_extra_argument_is_a_usage_error() -> None:
    handler = cli.Handler(FakeClientScripted())
    with pytest.raises(UsageError):
        handler.check(CliRequest(args=("/repo", "extra")))


def test_trees_prints_one_tree_per_line() -> None:
    handler = cli.Handler(FakeClientScripted(trees=("appone", "libby")))
    response = handler.trees(CliRequest(args=("/repo",)))
    assert response.exit_code == 0
    assert response.stdout == "appone\nlibby"
