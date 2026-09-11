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


class Rejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ERRORS: typing.Final[tuple[type[Rejected]]] = (Rejected,)


class AlphaClient(ts.Client, typing.Protocol):

    def add(self, add_request: AddRequest) -> AddResponse: ...
