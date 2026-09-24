from __future__ import annotations

import json
import typing

import tesser.application as ts


class RegisterWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class RegisterWidgetRequestSnapshot(ts.Serde):

    def serialize(self, register_widget_request: RegisterWidgetRequest) -> bytes:
        return json.dumps({"name": register_widget_request.name}).encode()

    def deserialize(self, buf: bytes) -> RegisterWidgetRequest:
        snapshot = json.loads(buf)
        return RegisterWidgetRequest(name=snapshot["name"])


class RegisterWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class RegisterWidgetResponseSnapshot(ts.Serde):

    def serialize(self, register_widget_response: RegisterWidgetResponse) -> bytes:
        return json.dumps({"name": register_widget_response.name}).encode()

    def deserialize(self, buf: bytes) -> RegisterWidgetResponse:
        snapshot = json.loads(buf)
        return RegisterWidgetResponse(name=snapshot["name"])


class ApproveWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class ApproveWidgetRequestSnapshot(ts.Serde):

    def serialize(self, approve_widget_request: ApproveWidgetRequest) -> bytes:
        return json.dumps({"name": approve_widget_request.name}).encode()

    def deserialize(self, buf: bytes) -> ApproveWidgetRequest:
        snapshot = json.loads(buf)
        return ApproveWidgetRequest(name=snapshot["name"])


class ApproveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class ApproveWidgetResponseSnapshot(ts.Serde):

    def serialize(self, approve_widget_response: ApproveWidgetResponse) -> bytes:
        return json.dumps({"name": approve_widget_response.name}).encode()

    def deserialize(self, buf: bytes) -> ApproveWidgetResponse:
        snapshot = json.loads(buf)
        return ApproveWidgetResponse(name=snapshot["name"])


class WidgetOrchestratorRelay(ts.Relay, typing.Protocol):

    async def run_register_widget(
        self, register_widget_request: RegisterWidgetRequest
    ) -> RegisterWidgetResponse: ...

    async def run_approve_widget(self, approve_widget_request: ApproveWidgetRequest) -> ApproveWidgetResponse: ...
