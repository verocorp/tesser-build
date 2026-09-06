from __future__ import annotations

import typing

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, key: str) -> None:
        self.key = key


class CheckResponse(ts.Response):

    def __init__(self, held: str) -> None:
        self.held = held


class BetaClient(ts.Client, typing.Protocol):

    def check(self, check_request: CheckRequest) -> CheckResponse: ...
