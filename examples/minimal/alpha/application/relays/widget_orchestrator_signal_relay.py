from __future__ import annotations

import json
import typing

import tesser.application as ts

APPROVE_WIDGET_PROMISE: typing.Final[str] = "approve_widget"


class AwaitApproveWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class AwaitApproveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class AwaitApproveWidgetResponseSnapshot(ts.Serde):

    def serialize(self, await_approve_widget_response: AwaitApproveWidgetResponse) -> bytes:
        return json.dumps({"name": await_approve_widget_response.name}).encode()

    def deserialize(self, buf: bytes) -> AwaitApproveWidgetResponse:
        snapshot = json.loads(buf)
        return AwaitApproveWidgetResponse(name=snapshot["name"])


class WidgetOrchestratorSignalRelay(ts.Relay, typing.Protocol):

    async def await_approve_widget(
        self, await_approve_widget_request: AwaitApproveWidgetRequest
    ) -> AwaitApproveWidgetResponse: ...
