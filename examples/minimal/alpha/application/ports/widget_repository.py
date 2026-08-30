from __future__ import annotations

import typing

import tesser.application as ts


class SaveRequest(ts.Request):

    def __init__(self, name: str, standing: str) -> None:
        self.name = name
        self.standing = standing


class SaveResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetRepository(ts.Port, typing.Protocol):

    def save(self, request: SaveRequest) -> SaveResponse: ...
