from __future__ import annotations

import datetime

import tesser.adapters as ts
import restate

import calls.adapters.runtimes as runtimes
import calls.application.relays as relays


class RestateAwaitCallRelays(ts.Runner):  # tesser:debt TB085

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_call_runtime: runtimes.RestateCallRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_call_runtime = restate_call_runtime

    async def await_person_answered(
        self, await_person_answered_request: relays.AwaitPersonAnsweredRequest
    ) -> relays.AwaitPersonAnsweredResponse:
        return await self._restate_workflow_context.promise(
            self._restate_call_runtime.person_answered_promise,
            serde=runtimes.RestateAwaitPersonAnsweredResponseSerde(),
        ).value()

    async def await_person_utterance(
        self, await_person_utterance_request: relays.AwaitPersonUtteranceRequest
    ) -> relays.AwaitPersonUtteranceResponse:
        awakeable_id, awaited = self._restate_workflow_context.awakeable(
            serde=runtimes.RestateAwaitPersonUtteranceResponseSerde()
        )
        self._restate_workflow_context.object_send(
            self._restate_call_runtime.take_person_utterance_handler,
            key=await_person_utterance_request.call_id,
            arg=awakeable_id,
        )
        self._restate_workflow_context.object_send(
            self._restate_call_runtime.stop_taking_person_utterance_handler,
            key=await_person_utterance_request.call_id,
            arg=awakeable_id,
            send_delay=datetime.timedelta(seconds=await_person_utterance_request.within_seconds),
        )
        return await awaited
