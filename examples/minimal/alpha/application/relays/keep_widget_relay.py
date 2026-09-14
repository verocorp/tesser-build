from __future__ import annotations

import typing

import tesser.application as ts


class KeepWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class KeepWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class KeepWidgetRelay(ts.Relay, typing.Protocol):

    def run_keep_widget(self, keep_widget_request: KeepWidgetRequest) -> KeepWidgetResponse: ...
