from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.application.client as client
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"


class RestateDialPersonRequestSerde(ts.Serde, restate_serde.Serde[relays.DialPersonRequest]):
    def serialize(self, dial_person_request: relays.DialPersonRequest | None) -> bytes:
        if dial_person_request is None:
            return b""
        return relays.DialPersonRequestSnapshot().serialize(dial_person_request)

    def deserialize(self, buf: bytes) -> relays.DialPersonRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.DialPersonRequestSnapshot().deserialize(buf)


class RestateDialPersonResponseSerde(ts.Serde, restate_serde.Serde[relays.DialPersonResponse]):
    def serialize(self, dial_person_response: relays.DialPersonResponse | None) -> bytes:
        if dial_person_response is None:
            return b""
        return relays.DialPersonResponseSnapshot().serialize(dial_person_response)

    def deserialize(self, buf: bytes) -> relays.DialPersonResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.DialPersonResponseSnapshot().deserialize(buf)


class RestateDialPerson(ts.A):
    def __init__(
        self, dialing_actions_service: restate.Service, dialing_application_client: client.DialingApplicationClient
    ) -> None:
        @dialing_actions_service.handler(
            input_serde=RestateDialPersonRequestSerde(),
            output_serde=RestateDialPersonResponseSerde(),
        )
        async def dial_person(
            restate_context: restate.Context, dial_person_request: relays.DialPersonRequest
        ) -> relays.DialPersonResponse:
            return await dialing_application_client.dial_person(dial_person_request)

        self.handler = dial_person
