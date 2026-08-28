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


class Client(ts.Client, typing.Protocol):

    async def check(self, request: CheckRequest) -> CheckResponse: ...

    async def hold(self, request: HoldRequest) -> HoldResponse: ...
