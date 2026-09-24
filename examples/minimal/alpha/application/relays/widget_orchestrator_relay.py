from __future__ import annotations

import typing

import tesser.application as ts


class RegisterWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class RegisterWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class ApproveWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class ApproveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetOrchestratorRelay(ts.Relay, typing.Protocol):

    def run_register_widget(self, register_widget_request: RegisterWidgetRequest) -> RegisterWidgetResponse: ...

    def run_approve_widget(self, approve_widget_request: ApproveWidgetRequest) -> ApproveWidgetResponse: ...
