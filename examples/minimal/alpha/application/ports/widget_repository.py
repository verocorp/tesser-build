from __future__ import annotations

import typing

import tesser.application as ts


class SaveWidgetRequest(ts.Request):

    def __init__(self, name: str, standing: str) -> None:
        self.name = name
        self.standing = standing


class SaveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetRepository(ts.Port, typing.Protocol):

    def save_widget(self, save_widget_request: SaveWidgetRequest) -> SaveWidgetResponse: ...
