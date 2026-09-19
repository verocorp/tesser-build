from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.adapters.runners as runners
import calls.application.client as client
import calls.application.orchestrators as orchestrators
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"
_RETRY_POLICY: typing.Final[restate.InvocationRetryPolicy] = restate.InvocationRetryPolicy(
    max_attempts=5, on_max_attempts="pause"
)
_PERSON_ANSWERED_PROMISE: typing.Final[str] = "person_answered"
_BUFFERED_PERSON_INPUTS: typing.Final[str] = "buffered"
_WAITING_AWAKEABLE: typing.Final[str] = "waiting"
_ALREADY_TAKING: typing.Final[str] = "another take of this call's utterances is already waiting"


class RestateConductCallRequestSerde(ts.Serde, restate_serde.Serde[relays.ConductCallRequest]):
    def serialize(self, conduct_call_request: relays.ConductCallRequest | None) -> bytes:
        if conduct_call_request is None:
            return b""
        return relays.ConductCallRequestSnapshot().serialize(conduct_call_request)

    def deserialize(self, buf: bytes) -> relays.ConductCallRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.ConductCallRequestSnapshot().deserialize(buf)


class RestateConductCallResponseSerde(ts.Serde, restate_serde.Serde[relays.ConductCallResponse]):
    def serialize(self, conduct_call_response: relays.ConductCallResponse | None) -> bytes:
        if conduct_call_response is None:
            return b""
        return relays.ConductCallResponseSnapshot().serialize(conduct_call_response)

    def deserialize(self, buf: bytes) -> relays.ConductCallResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.ConductCallResponseSnapshot().deserialize(buf)


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


class RestateSpeakTurnRequestSerde(ts.Serde, restate_serde.Serde[relays.SpeakTurnRequest]):
    def serialize(self, speak_turn_request: relays.SpeakTurnRequest | None) -> bytes:
        if speak_turn_request is None:
            return b""
        return relays.SpeakTurnRequestSnapshot().serialize(speak_turn_request)

    def deserialize(self, buf: bytes) -> relays.SpeakTurnRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.SpeakTurnRequestSnapshot().deserialize(buf)


class RestateSpeakTurnResponseSerde(ts.Serde, restate_serde.Serde[relays.SpeakTurnResponse]):
    def serialize(self, speak_turn_response: relays.SpeakTurnResponse | None) -> bytes:
        if speak_turn_response is None:
            return b""
        return relays.SpeakTurnResponseSnapshot().serialize(speak_turn_response)

    def deserialize(self, buf: bytes) -> relays.SpeakTurnResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.SpeakTurnResponseSnapshot().deserialize(buf)


class RestateInterpretTurnRequestSerde(ts.Serde, restate_serde.Serde[relays.InterpretTurnRequest]):
    def serialize(self, interpret_turn_request: relays.InterpretTurnRequest | None) -> bytes:
        if interpret_turn_request is None:
            return b""
        return relays.InterpretTurnRequestSnapshot().serialize(interpret_turn_request)

    def deserialize(self, buf: bytes) -> relays.InterpretTurnRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.InterpretTurnRequestSnapshot().deserialize(buf)


class RestateInterpretTurnResponseSerde(ts.Serde, restate_serde.Serde[relays.InterpretTurnResponse]):
    def serialize(self, interpret_turn_response: relays.InterpretTurnResponse | None) -> bytes:
        if interpret_turn_response is None:
            return b""
        return relays.InterpretTurnResponseSnapshot().serialize(interpret_turn_response)

    def deserialize(self, buf: bytes) -> relays.InterpretTurnResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.InterpretTurnResponseSnapshot().deserialize(buf)


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


class RestatePersonAnsweredRequestSerde(ts.Serde, restate_serde.Serde[relays.PersonAnsweredRequest]):
    def serialize(self, person_answered_request: relays.PersonAnsweredRequest | None) -> bytes:
        if person_answered_request is None:
            return b""
        return relays.PersonAnsweredRequestSnapshot().serialize(person_answered_request)

    def deserialize(self, buf: bytes) -> relays.PersonAnsweredRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonAnsweredRequestSnapshot().deserialize(buf)


class RestatePersonAnsweredResponseSerde(ts.Serde, restate_serde.Serde[relays.PersonAnsweredResponse]):
    def serialize(self, person_answered_response: relays.PersonAnsweredResponse | None) -> bytes:
        if person_answered_response is None:
            return b""
        return relays.PersonAnsweredResponseSnapshot().serialize(person_answered_response)

    def deserialize(self, buf: bytes) -> relays.PersonAnsweredResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonAnsweredResponseSnapshot().deserialize(buf)


class RestatePersonInputRequestSerde(ts.Serde, restate_serde.Serde[relays.PersonInputRequest]):
    def serialize(self, person_input_request: relays.PersonInputRequest | None) -> bytes:
        if person_input_request is None:
            return b""
        return relays.PersonInputRequestSnapshot().serialize(person_input_request)

    def deserialize(self, buf: bytes) -> relays.PersonInputRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonInputRequestSnapshot().deserialize(buf)


class RestatePersonInputResponseSerde(ts.Serde, restate_serde.Serde[relays.PersonInputResponse]):
    def serialize(self, person_input_response: relays.PersonInputResponse | None) -> bytes:
        if person_input_response is None:
            return b""
        return relays.PersonInputResponseSnapshot().serialize(person_input_response)

    def deserialize(self, buf: bytes) -> relays.PersonInputResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonInputResponseSnapshot().deserialize(buf)


class RestateAwaitPersonAnsweredResponseSerde(ts.Serde, restate_serde.Serde[relays.AwaitPersonAnsweredResponse]):
    def serialize(self, await_person_answered_response: relays.AwaitPersonAnsweredResponse | None) -> bytes:
        if await_person_answered_response is None:
            return b""
        return relays.AwaitPersonAnsweredResponseSnapshot().serialize(await_person_answered_response)

    def deserialize(self, buf: bytes) -> relays.AwaitPersonAnsweredResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.AwaitPersonAnsweredResponseSnapshot().deserialize(buf)


class RestateAwaitPersonInputResponseSerde(ts.Serde, restate_serde.Serde[relays.AwaitPersonInputResponse]):
    def serialize(self, await_person_input_response: relays.AwaitPersonInputResponse | None) -> bytes:
        if await_person_input_response is None:
            return b""
        return relays.AwaitPersonInputResponseSnapshot().serialize(await_person_input_response)

    def deserialize(self, buf: bytes) -> relays.AwaitPersonInputResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.AwaitPersonInputResponseSnapshot().deserialize(buf)


class RestateCallRuntime(ts.Runtime):
    def __init__(
        self,
        call_application_client: client.CallApplicationClient,
        dialing_application_client: client.DialingApplicationClient,
        speech_application_client: client.SpeechApplicationClient,
        interpretation_application_client: client.InterpretationApplicationClient,
    ) -> None:
        self.call_actions_service = restate.Service("CallActions", invocation_retry_policy=_RETRY_POLICY)
        self.dialing_actions_service = restate.Service("DialingActions", invocation_retry_policy=_RETRY_POLICY)
        self.interpretation_actions_service = restate.Service(
            "InterpretationActions", invocation_retry_policy=_RETRY_POLICY
        )
        self.speech_actions_service = restate.Service("SpeechActions", invocation_retry_policy=_RETRY_POLICY)
        self.call_orchestrator_workflow = restate.Workflow("CallOrchestrator", invocation_retry_policy=_RETRY_POLICY)
        self.call_inputs_object = restate.VirtualObject("CallInputs", invocation_retry_policy=_RETRY_POLICY)
        self.person_answered_promise = _PERSON_ANSWERED_PROMISE

        @self.call_actions_service.handler(
            input_serde=RestateRecordCallRequestSerde(),
            output_serde=RestateRecordCallResponseSerde(),
        )
        async def record_call(
            restate_context: restate.Context, record_call_request: relays.RecordCallRequest
        ) -> relays.RecordCallResponse:
            return await call_application_client.record_call(record_call_request)

        @self.dialing_actions_service.handler(
            input_serde=RestateDialPersonRequestSerde(),
            output_serde=RestateDialPersonResponseSerde(),
        )
        async def dial_person(
            restate_context: restate.Context, dial_person_request: relays.DialPersonRequest
        ) -> relays.DialPersonResponse:
            return await dialing_application_client.dial_person(dial_person_request)

        @self.dialing_actions_service.handler(
            input_serde=RestateHangUpRequestSerde(),
            output_serde=RestateHangUpResponseSerde(),
        )
        async def hang_up(
            restate_context: restate.Context, hang_up_request: relays.HangUpRequest
        ) -> relays.HangUpResponse:
            return await dialing_application_client.hang_up(hang_up_request)

        @self.speech_actions_service.handler(
            input_serde=RestateSpeakTurnRequestSerde(),
            output_serde=RestateSpeakTurnResponseSerde(),
        )
        async def speak_turn(
            restate_context: restate.Context, speak_turn_request: relays.SpeakTurnRequest
        ) -> relays.SpeakTurnResponse:
            return await speech_application_client.speak_turn(speak_turn_request)

        @self.interpretation_actions_service.handler(
            input_serde=RestateInterpretTurnRequestSerde(),
            output_serde=RestateInterpretTurnResponseSerde(),
        )
        async def interpret_turn(
            restate_context: restate.Context, interpret_turn_request: relays.InterpretTurnRequest
        ) -> relays.InterpretTurnResponse:
            return await interpretation_application_client.interpret_turn(interpret_turn_request)

        @self.call_orchestrator_workflow.main(
            input_serde=RestateConductCallRequestSerde(),
            output_serde=RestateConductCallResponseSerde(),
        )
        async def conduct_call(
            restate_workflow_context: restate.WorkflowContext, conduct_call_request: relays.ConductCallRequest
        ) -> relays.ConductCallResponse:
            return await orchestrators.CallOrchestrator(
                runners.RestateInvocationDialingRelay(restate_workflow_context, self),
                runners.RestateInvocationSpeechRelay(restate_workflow_context, self),
                runners.RestateInvocationPersonRelay(restate_workflow_context, self),
                runners.RestateInvocationRecordCallRelay(restate_workflow_context, self),
                runners.RestateInvocationInterpretationRelay(restate_workflow_context, self),
            ).conduct_call(conduct_call_request)

        @self.call_orchestrator_workflow.handler(
            input_serde=RestatePersonAnsweredRequestSerde(),
            output_serde=RestatePersonAnsweredResponseSerde(),
        )
        async def person_answered(  # tesser:debt TB085
            restate_workflow_shared_context: restate.WorkflowSharedContext,
            person_answered_request: relays.PersonAnsweredRequest,
        ) -> relays.PersonAnsweredResponse:
            person_answered_promise = restate_workflow_shared_context.promise(
                _PERSON_ANSWERED_PROMISE, serde=RestateAwaitPersonAnsweredResponseSerde()
            )
            if await person_answered_promise.peek() is None:
                await person_answered_promise.resolve(
                    relays.AwaitPersonAnsweredResponse(call_id=person_answered_request.call_id)
                )
            return relays.PersonAnsweredResponse(call_id=person_answered_request.call_id)

        @self.call_inputs_object.handler(
            input_serde=RestatePersonInputRequestSerde(),
            output_serde=RestatePersonInputResponseSerde(),
        )
        async def person_input(  # tesser:debt TB085
            restate_object_context: restate.ObjectContext, person_input_request: relays.PersonInputRequest
        ) -> relays.PersonInputResponse:
            waiting = await restate_object_context.get(_WAITING_AWAKEABLE, type_hint=str)
            if waiting is None:
                buffered = (
                    await restate_object_context.get(_BUFFERED_PERSON_INPUTS, type_hint=list[dict[str, str]]) or []
                )
                restate_object_context.set(
                    _BUFFERED_PERSON_INPUTS,
                    [*buffered, {"kind": person_input_request.kind, "text": person_input_request.text}],
                )
            else:
                restate_object_context.clear(_WAITING_AWAKEABLE)
                restate_object_context.resolve_awakeable(
                    waiting,
                    relays.AwaitPersonInputResponse(
                        call_id=person_input_request.call_id,
                        kind=person_input_request.kind,
                        text=person_input_request.text,
                    ),
                    serde=RestateAwaitPersonInputResponseSerde(),
                )
            return relays.PersonInputResponse(call_id=person_input_request.call_id)

        @self.call_inputs_object.handler()
        async def take_person_input(  # tesser:debt TB085
            restate_object_context: restate.ObjectContext, awakeable_id: str
        ) -> None:
            waiting = await restate_object_context.get(_WAITING_AWAKEABLE, type_hint=str)
            buffered = await restate_object_context.get(_BUFFERED_PERSON_INPUTS, type_hint=list[dict[str, str]]) or []
            if waiting is not None:
                restate_object_context.reject_awakeable(awakeable_id, _ALREADY_TAKING)
            elif buffered:
                restate_object_context.set(_BUFFERED_PERSON_INPUTS, buffered[1:])
                restate_object_context.resolve_awakeable(
                    awakeable_id,
                    relays.AwaitPersonInputResponse(
                        call_id=restate_object_context.key(), kind=buffered[0]["kind"], text=buffered[0]["text"]
                    ),
                    serde=RestateAwaitPersonInputResponseSerde(),
                )
            else:
                restate_object_context.set(_WAITING_AWAKEABLE, awakeable_id)

        @self.call_inputs_object.handler()
        async def stop_taking_person_input(  # tesser:debt TB085
            restate_object_context: restate.ObjectContext, awakeable_id: str
        ) -> None:
            waiting = await restate_object_context.get(_WAITING_AWAKEABLE, type_hint=str)
            if waiting == awakeable_id:
                restate_object_context.clear(_WAITING_AWAKEABLE)
                restate_object_context.resolve_awakeable(
                    awakeable_id,
                    relays.AwaitPersonInputResponse(
                        call_id=restate_object_context.key(), kind=relays.INPUT_NO_RESPONSE, text=""
                    ),
                    serde=RestateAwaitPersonInputResponseSerde(),
                )

        self.record_call_handler = record_call
        self.dial_person_handler = dial_person
        self.hang_up_handler = hang_up
        self.speak_turn_handler = speak_turn
        self.interpret_turn_handler = interpret_turn
        self.conduct_call_handler = conduct_call
        self.person_answered_handler = person_answered
        self.person_input_handler = person_input
        self.take_person_input_handler = take_person_input
        self.stop_taking_person_input_handler = stop_taking_person_input
