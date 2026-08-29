from __future__ import annotations

import enum
import typing

import tesser.application as ts


class Found(enum.Enum):
    YES = "yes"
    NO = "no"


class SaveRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class SaveResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class FindRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class FindResponse(ts.Response):

    def __init__(self, found: Found) -> None:
        self.found = found


class WidgetRepository(ts.Port, typing.Protocol):

    async def save(self, request: SaveRequest) -> SaveResponse: ...

    async def find(self, request: FindRequest) -> FindResponse: ...
