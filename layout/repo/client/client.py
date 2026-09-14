from __future__ import annotations

import typing

import tesser.context as ts


class CheckLayoutRequest(ts.Request):

    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root


class CheckLayoutResponse(ts.Response):

    def __init__(self, problems: tuple[str, ...], counts: tuple[str, ...]) -> None:
        self.problems = problems
        self.counts = counts


class ListTreesRequest(ts.Request):

    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root


class ListTreesResponse(ts.Response):

    def __init__(self, trees: tuple[str, ...]) -> None:
        self.trees = trees


class RepoClient(ts.Client, typing.Protocol):

    def check_layout(self, check_layout_request: CheckLayoutRequest) -> CheckLayoutResponse: ...

    def list_trees(self, list_trees_request: ListTreesRequest) -> ListTreesResponse: ...
