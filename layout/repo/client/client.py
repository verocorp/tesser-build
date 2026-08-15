from __future__ import annotations

from typing import Protocol

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, root: str) -> None:
        self.root = root


class CheckResponse(ts.Response):

    def __init__(self, problems: tuple[str, ...], counts: tuple[str, ...]) -> None:
        self.problems = problems
        self.counts = counts


class TreesRequest(ts.Request):

    def __init__(self, root: str) -> None:
        self.root = root


class TreesResponse(ts.Response):

    def __init__(self, trees: tuple[str, ...]) -> None:
        self.trees = trees


class Client(ts.Client, Protocol):

    def check(self, request: CheckRequest) -> CheckResponse: ...

    def trees(self, request: TreesRequest) -> TreesResponse: ...
