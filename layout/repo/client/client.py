from __future__ import annotations

import typing

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root


class CheckResponse(ts.Response):

    def __init__(self, problems: tuple[str, ...], counts: tuple[str, ...]) -> None:
        self.problems = problems
        self.counts = counts


class TreesRequest(ts.Request):

    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root


class TreesResponse(ts.Response):

    def __init__(self, trees: tuple[str, ...]) -> None:
        self.trees = trees


class RepoClient(ts.Client, typing.Protocol):

    def check(self, check_request: CheckRequest) -> CheckResponse: ...

    def trees(self, trees_request: TreesRequest) -> TreesResponse: ...
