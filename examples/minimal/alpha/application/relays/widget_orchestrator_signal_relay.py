from __future__ import annotations

import typing

import tesser.application as ts

APPROVE_WIDGET_PROMISE: typing.Final[str] = "approve_widget"


class AwaitApproveWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class AwaitApproveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetOrchestratorSignalRelay(ts.Relay, typing.Protocol):

    def await_approve_widget(
        self, await_approve_widget_request: AwaitApproveWidgetRequest
    ) -> AwaitApproveWidgetResponse: ...
