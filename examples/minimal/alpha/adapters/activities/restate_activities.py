from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import alpha.application.client as client
import alpha.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"


class RestateKeepWidgetRequestSerde(ts.Serde, restate_serde.Serde[relays.KeepWidgetRequest]):

    def serialize(self, keep_widget_request: relays.KeepWidgetRequest | None) -> bytes:
        if keep_widget_request is None:
            return b""
        return relays.KeepWidgetRequestSnapshot().serialize(keep_widget_request)

    def deserialize(self, buf: bytes) -> relays.KeepWidgetRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.KeepWidgetRequestSnapshot().deserialize(buf)


class RestateKeepWidgetResponseSerde(ts.Serde, restate_serde.Serde[relays.KeepWidgetResponse]):

    def serialize(self, keep_widget_response: relays.KeepWidgetResponse | None) -> bytes:
        if keep_widget_response is None:
            return b""
        return relays.KeepWidgetResponseSnapshot().serialize(keep_widget_response)

    def deserialize(self, buf: bytes) -> relays.KeepWidgetResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.KeepWidgetResponseSnapshot().deserialize(buf)


class RestateKeepWidget(ts.Activity):

    def __init__(
        self, widget_actions_service: restate.Service, widget_application_client: client.WidgetApplicationClient
    ) -> None:
        @widget_actions_service.handler(
            input_serde=RestateKeepWidgetRequestSerde(),
            output_serde=RestateKeepWidgetResponseSerde(),
        )
        async def keep_widget(
            restate_context: restate.Context, keep_widget_request: relays.KeepWidgetRequest
        ) -> relays.KeepWidgetResponse:
            return await widget_application_client.keep_widget(keep_widget_request)

        self.handler = keep_widget
