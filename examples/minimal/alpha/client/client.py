from __future__ import annotations

import typing

import tesser.context as ts


class WholeView(ts.Response):

    def __init__(self, id: str, name: str, count: int) -> None:
        self.id = id
        self.name = name
        self.count = count


class AddRequest(ts.Request):

    def __init__(self, id: str, name: str, count: int) -> None:
        self.id = id
        self.name = name
        self.count = count


class AddResponse(ts.Response):

    def __init__(self, wholes: tuple[WholeView, ...]) -> None:
        self.wholes = wholes


class GetRequest(ts.Request):

    def __init__(self, id: str) -> None:
        self.id = id


class GetResponse(ts.Response):

    def __init__(self, wholes: tuple[WholeView, ...]) -> None:
        self.wholes = wholes


class Client(ts.Client, typing.Protocol):

    def add(self, request: AddRequest) -> AddResponse: ...

    def get(self, request: GetRequest) -> GetResponse: ...
