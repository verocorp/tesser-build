from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.application.client as client
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"
_FOREIGN_CALL_ID: typing.Final[str] = "a message names the call its workflow is keyed by"
_ALREADY_COMPLETED: typing.Final[int] = 409
_RETRY_POLICY: typing.Final[restate.InvocationRetryPolicy] = restate.InvocationRetryPolicy(
    max_attempts=5, on_max_attempts="pause"
)


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


class RestatePersonJoinedRequestSerde(ts.Serde, restate_serde.Serde[relays.PersonJoinedRequest]):
    def serialize(self, person_joined_request: relays.PersonJoinedRequest | None) -> bytes:
        if person_joined_request is None:
            return b""
        return relays.PersonJoinedRequestSnapshot().serialize(person_joined_request)

    def deserialize(self, buf: bytes) -> relays.PersonJoinedRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonJoinedRequestSnapshot().deserialize(buf)


class RestatePersonJoinedResponseSerde(ts.Serde, restate_serde.Serde[relays.PersonJoinedResponse]):
    def serialize(self, person_joined_response: relays.PersonJoinedResponse | None) -> bytes:
        if person_joined_response is None:
            return b""
        return relays.PersonJoinedResponseSnapshot().serialize(person_joined_response)

    def deserialize(self, buf: bytes) -> relays.PersonJoinedResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonJoinedResponseSnapshot().deserialize(buf)


class RestatePersonTurnCompletedRequestSerde(ts.Serde, restate_serde.Serde[relays.PersonTurnCompletedRequest]):
    def serialize(self, person_turn_completed_request: relays.PersonTurnCompletedRequest | None) -> bytes:
        if person_turn_completed_request is None:
            return b""
        return relays.PersonTurnCompletedRequestSnapshot().serialize(person_turn_completed_request)

    def deserialize(self, buf: bytes) -> relays.PersonTurnCompletedRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonTurnCompletedRequestSnapshot().deserialize(buf)


class RestatePersonTurnCompletedResponseSerde(ts.Serde, restate_serde.Serde[relays.PersonTurnCompletedResponse]):
    def serialize(self, person_turn_completed_response: relays.PersonTurnCompletedResponse | None) -> bytes:
        if person_turn_completed_response is None:
            return b""
        return relays.PersonTurnCompletedResponseSnapshot().serialize(person_turn_completed_response)

    def deserialize(self, buf: bytes) -> relays.PersonTurnCompletedResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonTurnCompletedResponseSnapshot().deserialize(buf)


class RestateCallRuntime(ts.Runtime):
    def __init__(
        self,
        call_application_client: client.CallApplicationClient,
        dialing_application_client: client.DialingApplicationClient,
        speech_application_client: client.SpeechApplicationClient,
        call_workflow: client.CallWorkflow[restate.WorkflowContext],
    ) -> None:
        self.call_actions_service = restate.Service("CallActions", invocation_retry_policy=_RETRY_POLICY)
        self.dialing_actions_service = restate.Service("DialingActions", invocation_retry_policy=_RETRY_POLICY)
        self.speech_actions_service = restate.Service("SpeechActions", invocation_retry_policy=_RETRY_POLICY)
        self.call_orchestrator_workflow = restate.Workflow("CallOrchestrator", invocation_retry_policy=_RETRY_POLICY)

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
            input_serde=RestateSayUtteranceRequestSerde(),
            output_serde=RestateSayUtteranceResponseSerde(),
        )
        async def say_utterance(
            restate_context: restate.Context, say_utterance_request: relays.SayUtteranceRequest
        ) -> relays.SayUtteranceResponse:
            return await speech_application_client.say_utterance(say_utterance_request)

        @self.call_orchestrator_workflow.main(
            input_serde=RestateConductCallRequestSerde(),
            output_serde=RestateConductCallResponseSerde(),
        )
        async def conduct_call(
            restate_workflow_context: restate.WorkflowContext, conduct_call_request: relays.ConductCallRequest
        ) -> relays.ConductCallResponse:
            async with call_workflow.invocation(restate_workflow_context) as call_orchestrator_application_client:
                return await call_orchestrator_application_client.conduct_call(conduct_call_request)

        @self.call_orchestrator_workflow.handler(
            input_serde=RestatePersonJoinedRequestSerde(),
            output_serde=RestatePersonJoinedResponseSerde(),
        )
        async def person_joined(  # tesser:debt TB085
            restate_workflow_shared_context: restate.WorkflowSharedContext,
            person_joined_request: relays.PersonJoinedRequest,
        ) -> relays.PersonJoinedResponse:
            call_id = restate_workflow_shared_context.key()
            if person_joined_request.call_id != call_id:
                raise restate.TerminalError(_FOREIGN_CALL_ID, status_code=400)
            try:
                await restate_workflow_shared_context.promise("person_joined", serde=restate_serde.BytesSerde()).resolve(
                    relays.AwaitPersonJoinedResponseSnapshot().serialize(relays.AwaitPersonJoinedResponse(call_id=call_id))
                )
            except restate.TerminalError as terminal_error:
                if terminal_error.status_code != _ALREADY_COMPLETED:
                    raise
            return relays.PersonJoinedResponse(call_id=call_id)

        @self.call_orchestrator_workflow.handler(
            input_serde=RestatePersonTurnCompletedRequestSerde(),
            output_serde=RestatePersonTurnCompletedResponseSerde(),
        )
        async def person_turn_completed(  # tesser:debt TB085
            restate_workflow_shared_context: restate.WorkflowSharedContext,
            person_turn_completed_request: relays.PersonTurnCompletedRequest,
        ) -> relays.PersonTurnCompletedResponse:
            call_id = restate_workflow_shared_context.key()
            if person_turn_completed_request.call_id != call_id:
                raise restate.TerminalError(_FOREIGN_CALL_ID, status_code=400)
            try:
                await restate_workflow_shared_context.promise(
                    "person_turn_completed", serde=restate_serde.BytesSerde()
                ).resolve(
                    relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                        relays.AwaitPersonTurnCompletedResponse(call_id=call_id, text=person_turn_completed_request.text)
                    )
                )
            except restate.TerminalError as terminal_error:
                if terminal_error.status_code != _ALREADY_COMPLETED:
                    raise
            return relays.PersonTurnCompletedResponse(call_id=call_id)

        self.record_call_handler = record_call
        self.dial_person_handler = dial_person
        self.hang_up_handler = hang_up
        self.say_utterance_handler = say_utterance
        self.conduct_call_handler = conduct_call
        self.person_joined_handler = person_joined
        self.person_turn_completed_handler = person_turn_completed
