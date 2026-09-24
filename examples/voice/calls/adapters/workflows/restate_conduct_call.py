from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.adapters.activities as activities
import calls.application.orchestrators as orchestrators
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"


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


class RestateInvocationCallActionsRelay(ts.Dispatcher):
    def __init__(
        self, restate_workflow_context: restate.WorkflowContext, restate_record_call: activities.RestateRecordCall
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_record_call = restate_record_call

    async def run_record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        return await self._restate_workflow_context.service_call(self._restate_record_call.handler, record_call_request)


class RestateInvocationDialingActionsRelay(ts.Dispatcher):
    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_dial_person: activities.RestateDialPerson,
        restate_hang_up: activities.RestateHangUp,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_dial_person = restate_dial_person
        self._restate_hang_up = restate_hang_up

    async def run_dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        return await self._restate_workflow_context.service_call(self._restate_dial_person.handler, dial_person_request)

    async def run_hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        return await self._restate_workflow_context.service_call(self._restate_hang_up.handler, hang_up_request)


class RestateInvocationSpeechActionsRelay(ts.Dispatcher):
    def __init__(
        self, restate_workflow_context: restate.WorkflowContext, restate_say_utterance: activities.RestateSayUtterance
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_say_utterance = restate_say_utterance

    async def run_say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        return await self._restate_workflow_context.service_call(
            self._restate_say_utterance.handler, say_utterance_request
        )


class RestateInvocationCallOrchestratorSignalRelay(ts.Dispatcher):
    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def await_person_joined(
        self, await_person_joined_request: relays.AwaitPersonJoinedRequest
    ) -> relays.AwaitPersonJoinedResponse:
        return relays.AwaitPersonJoinedResponseSnapshot().deserialize(
            await self._restate_workflow_context.promise(
                relays.PERSON_JOINED_PROMISE, serde=restate_serde.BytesSerde()
            ).value()
        )

    async def await_person_turn_completed(
        self, await_person_turn_completed_request: relays.AwaitPersonTurnCompletedRequest
    ) -> relays.AwaitPersonTurnCompletedResponse:
        return relays.AwaitPersonTurnCompletedResponseSnapshot().deserialize(
            await self._restate_workflow_context.promise(
                relays.PERSON_TURN_COMPLETED_PROMISE, serde=restate_serde.BytesSerde()
            ).value()
        )


class RestateConductCall(ts.Workflow):
    def __init__(
        self,
        call_orchestrator_workflow: restate.Workflow,
        restate_record_call: activities.RestateRecordCall,
        restate_dial_person: activities.RestateDialPerson,
        restate_hang_up: activities.RestateHangUp,
        restate_say_utterance: activities.RestateSayUtterance,
    ) -> None:
        @call_orchestrator_workflow.main(
            input_serde=RestateConductCallRequestSerde(),
            output_serde=RestateConductCallResponseSerde(),
        )
        async def conduct_call(
            restate_workflow_context: restate.WorkflowContext, conduct_call_request: relays.ConductCallRequest
        ) -> relays.ConductCallResponse:
            restate_workflow_context.set(
                relays.CONDUCT_CALL_STATE,
                relays.ConductCallRequestSnapshot().serialize(conduct_call_request),
                serde=restate_serde.BytesSerde(),
            )
            return await orchestrators.CallOrchestrator(
                RestateInvocationDialingActionsRelay(restate_workflow_context, restate_dial_person, restate_hang_up),
                RestateInvocationCallOrchestratorSignalRelay(restate_workflow_context),
                RestateInvocationSpeechActionsRelay(restate_workflow_context, restate_say_utterance),
                RestateInvocationCallActionsRelay(restate_workflow_context, restate_record_call),
            ).conduct_call(conduct_call_request)

        self.handler = conduct_call
