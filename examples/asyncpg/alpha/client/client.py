from __future__ import annotations

import typing

import tesser.context as ts


class AddRequest(ts.Request):

    def __init__(self, name: str, part: str) -> None:
        self.name = name
        self.part = part


class AddResponse(ts.Response):

    def __init__(self, name: str, standing: str) -> None:
        self.name = name
        self.standing = standing


class TakeRequest(ts.Request):

    def __init__(self, name: str, part: str) -> None:
        self.name = name
        self.part = part


class TakeResponse(ts.Response):

    def __init__(self, name: str, part: str, standing: str) -> None:
        self.name = name
        self.part = part
        self.standing = standing


class FindRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class FindResponse(ts.Response):

    def __init__(self, found: str) -> None:
        self.found = found


class Client(ts.Client, typing.Protocol):

    async def add(self, request: AddRequest) -> AddResponse: ...

    async def take(self, request: TakeRequest) -> TakeResponse: ...

    async def find(self, request: FindRequest) -> FindResponse: ...
