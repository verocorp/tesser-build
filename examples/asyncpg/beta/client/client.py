from __future__ import annotations

import typing

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, key: str) -> None:
        self.key = key


class CheckResponse(ts.Response):

    def __init__(self, held: str) -> None:
        self.held = held


class HoldRequest(ts.Request):

    def __init__(self, key: str) -> None:
        self.key = key


class HoldResponse(ts.Response):

    def __init__(self, key: str) -> None:
        self.key = key


class Rejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ERRORS: typing.Final[tuple[type[Rejected]]] = (Rejected,)


class BetaClient(ts.Client, typing.Protocol):

    async def check(self, check_request: CheckRequest) -> CheckResponse: ...

    async def hold(self, hold_request: HoldRequest) -> HoldResponse: ...
