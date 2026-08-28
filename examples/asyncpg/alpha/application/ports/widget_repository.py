from __future__ import annotations

import typing

import tesser.application as ts


class SaveRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class SaveResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetRepository(ts.Port, typing.Protocol):

    async def save(self, request: SaveRequest) -> SaveResponse: ...
