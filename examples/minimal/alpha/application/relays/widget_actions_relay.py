from __future__ import annotations

import json
import typing

import tesser.application as ts


class KeepWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class KeepWidgetRequestSnapshot(ts.Serde):

    def serialize(self, keep_widget_request: KeepWidgetRequest) -> bytes:
        return json.dumps({"name": keep_widget_request.name}).encode()

    def deserialize(self, buf: bytes) -> KeepWidgetRequest:
        snapshot = json.loads(buf)
        return KeepWidgetRequest(name=snapshot["name"])


class KeepWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class KeepWidgetResponseSnapshot(ts.Serde):

    def serialize(self, keep_widget_response: KeepWidgetResponse) -> bytes:
        return json.dumps({"name": keep_widget_response.name}).encode()

    def deserialize(self, buf: bytes) -> KeepWidgetResponse:
        snapshot = json.loads(buf)
        return KeepWidgetResponse(name=snapshot["name"])


class WidgetActionsRelay(ts.Relay, typing.Protocol):

    async def run_keep_widget(self, keep_widget_request: KeepWidgetRequest) -> KeepWidgetResponse: ...
