from __future__ import annotations

import typing

import tesser.context as ts


class AddRequest(ts.Request):

    def __init__(self, name: str, part: str) -> None:
        self.name = name
        self.part = part


class AddResponse(ts.Response):

    def __init__(self, name: str, part: str, standing: str) -> None:
        self.name = name
        self.part = part
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


class Rejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Missing(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Conflict(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ERRORS: typing.Final[tuple[type[Rejected], type[Missing], type[Conflict]]] = (
    Rejected,
    Missing,
    Conflict,
)


class AlphaClient(ts.Client, typing.Protocol):

    async def add(self, add_request: AddRequest) -> AddResponse: ...

    async def take(self, take_request: TakeRequest) -> TakeResponse: ...

    async def find(self, find_request: FindRequest) -> FindResponse: ...
