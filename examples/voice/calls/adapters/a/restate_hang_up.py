from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.application.client as client
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"


class RestateHangUpRequestSerde(ts.Serde, restate_serde.Serde[relays.HangUpRequest]):
    def serialize(self, hang_up_request: relays.HangUpRequest | None) -> bytes:
        if hang_up_request is None:
            return b""
        return relays.HangUpRequestSnapshot().serialize(hang_up_request)

    def deserialize(self, buf: bytes) -> relays.HangUpRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.HangUpRequestSnapshot().deserialize(buf)


class RestateHangUpResponseSerde(ts.Serde, restate_serde.Serde[relays.HangUpResponse]):
    def serialize(self, hang_up_response: relays.HangUpResponse | None) -> bytes:
        if hang_up_response is None:
            return b""
        return relays.HangUpResponseSnapshot().serialize(hang_up_response)

    def deserialize(self, buf: bytes) -> relays.HangUpResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.HangUpResponseSnapshot().deserialize(buf)


class RestateHangUp(ts.A):
    def __init__(
        self, dialing_actions_service: restate.Service, dialing_application_client: client.DialingApplicationClient
    ) -> None:
        @dialing_actions_service.handler(
            input_serde=RestateHangUpRequestSerde(),
            output_serde=RestateHangUpResponseSerde(),
        )
        async def hang_up(
            restate_context: restate.Context, hang_up_request: relays.HangUpRequest
        ) -> relays.HangUpResponse:
            return await dialing_application_client.hang_up(hang_up_request)

        self.handler = hang_up
