from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.application.client as client
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"


class RestateRecordCallRequestSerde(ts.Serde, restate_serde.Serde[relays.RecordCallRequest]):
    def serialize(self, record_call_request: relays.RecordCallRequest | None) -> bytes:
        if record_call_request is None:
            return b""
        return relays.RecordCallRequestSnapshot().serialize(record_call_request)

    def deserialize(self, buf: bytes) -> relays.RecordCallRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.RecordCallRequestSnapshot().deserialize(buf)


class RestateRecordCallResponseSerde(ts.Serde, restate_serde.Serde[relays.RecordCallResponse]):
    def serialize(self, record_call_response: relays.RecordCallResponse | None) -> bytes:
        if record_call_response is None:
            return b""
        return relays.RecordCallResponseSnapshot().serialize(record_call_response)

    def deserialize(self, buf: bytes) -> relays.RecordCallResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.RecordCallResponseSnapshot().deserialize(buf)


class RestateRecordCall(ts.Activity):
    def __init__(
        self, call_actions_service: restate.Service, call_application_client: client.CallApplicationClient
    ) -> None:
        @call_actions_service.handler(
            input_serde=RestateRecordCallRequestSerde(),
            output_serde=RestateRecordCallResponseSerde(),
        )
        async def record_call(
            restate_context: restate.Context, record_call_request: relays.RecordCallRequest
        ) -> relays.RecordCallResponse:
            return await call_application_client.record_call(record_call_request)

        self.handler = record_call


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


class RestateDialPerson(ts.Activity):
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


class RestateHangUp(ts.Activity):
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


class RestateSayUtterance(ts.Activity):
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
