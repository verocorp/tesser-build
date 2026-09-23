from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.application.client as client
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"


class RestateSayUtteranceRequestSerde(ts.Serde, restate_serde.Serde[relays.SayUtteranceRequest]):
    def serialize(self, say_utterance_request: relays.SayUtteranceRequest | None) -> bytes:
        if say_utterance_request is None:
            return b""
        return relays.SayUtteranceRequestSnapshot().serialize(say_utterance_request)

    def deserialize(self, buf: bytes) -> relays.SayUtteranceRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.SayUtteranceRequestSnapshot().deserialize(buf)


class RestateSayUtteranceResponseSerde(ts.Serde, restate_serde.Serde[relays.SayUtteranceResponse]):
    def serialize(self, say_utterance_response: relays.SayUtteranceResponse | None) -> bytes:
        if say_utterance_response is None:
            return b""
        return relays.SayUtteranceResponseSnapshot().serialize(say_utterance_response)

    def deserialize(self, buf: bytes) -> relays.SayUtteranceResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.SayUtteranceResponseSnapshot().deserialize(buf)


class RestateSayUtterance(ts.A):
    def __init__(
        self, speech_actions_service: restate.Service, speech_application_client: client.SpeechApplicationClient
    ) -> None:
        @speech_actions_service.handler(
            input_serde=RestateSayUtteranceRequestSerde(),
            output_serde=RestateSayUtteranceResponseSerde(),
        )
        async def say_utterance(
            restate_context: restate.Context, say_utterance_request: relays.SayUtteranceRequest
        ) -> relays.SayUtteranceResponse:
            return await speech_application_client.say_utterance(say_utterance_request)

        self.handler = say_utterance
