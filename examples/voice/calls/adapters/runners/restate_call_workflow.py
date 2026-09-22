from __future__ import annotations

import contextlib
import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.application.orchestrators as orchestrators
import calls.application.relays as relays


class RestateInvocationCallActionsRelay(ts.Runner):

    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def run_record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        return relays.RecordCallResponseSnapshot().deserialize(
            await self._restate_workflow_context.generic_call(
                "CallActions", "record_call", relays.RecordCallRequestSnapshot().serialize(record_call_request)
            )
        )


class RestateInvocationCallOrchestratorSignalRelay(ts.Runner):

    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def await_person_joined(
        self, await_person_joined_request: relays.AwaitPersonJoinedRequest
    ) -> relays.AwaitPersonJoinedResponse:
        return relays.AwaitPersonJoinedResponseSnapshot().deserialize(
            await self._restate_workflow_context.promise("person_joined", serde=restate_serde.BytesSerde()).value()
        )

    async def await_person_turn_completed(
        self, await_person_turn_completed_request: relays.AwaitPersonTurnCompletedRequest
    ) -> relays.AwaitPersonTurnCompletedResponse:
        return relays.AwaitPersonTurnCompletedResponseSnapshot().deserialize(
            await self._restate_workflow_context.promise(
                "person_turn_completed", serde=restate_serde.BytesSerde()
            ).value()
        )


class RestateInvocationDialingActionsRelay(ts.Runner):

    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def run_dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        return relays.DialPersonResponseSnapshot().deserialize(
            await self._restate_workflow_context.generic_call(
                "DialingActions", "dial_person", relays.DialPersonRequestSnapshot().serialize(dial_person_request)
            )
        )

    async def run_hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        return relays.HangUpResponseSnapshot().deserialize(
            await self._restate_workflow_context.generic_call(
                "DialingActions", "hang_up", relays.HangUpRequestSnapshot().serialize(hang_up_request)
            )
        )


class RestateInvocationSpeechActionsRelay(ts.Runner):

    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def run_say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        return relays.SayUtteranceResponseSnapshot().deserialize(
            await self._restate_workflow_context.generic_call(
                "SpeechActions",
                "say_utterance",
                relays.SayUtteranceRequestSnapshot().serialize(say_utterance_request),
            )
        )


class RestateCallWorkflow(ts.Runner):

    @contextlib.asynccontextmanager
    async def invocation(
        self, restate_workflow_context: restate.WorkflowContext
    ) -> typing.AsyncIterator[orchestrators.CallOrchestrator]:
        yield orchestrators.CallOrchestrator(
            RestateInvocationDialingActionsRelay(restate_workflow_context),
            RestateInvocationCallOrchestratorSignalRelay(restate_workflow_context),
            RestateInvocationSpeechActionsRelay(restate_workflow_context),
            RestateInvocationCallActionsRelay(restate_workflow_context),
        )
