from __future__ import annotations

import tesser.adapters as ts
import restate

import calls.adapters.runtimes as runtimes
import calls.application.relays as relays


class RestateInvocationPersonRelay(ts.Runner):
    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_call_runtime: runtimes.RestateCallRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_call_runtime = restate_call_runtime

    async def await_person_joined(
        self, await_person_joined_request: relays.AwaitPersonJoinedRequest
    ) -> relays.AwaitPersonJoinedResponse:
        return await self._restate_workflow_context.promise(
            self._restate_call_runtime.person_joined_promise,
            serde=runtimes.RestateAwaitPersonJoinedResponseSerde(),
        ).value()

    async def await_person_turn(
        self, await_person_turn_request: relays.AwaitPersonTurnRequest
    ) -> relays.AwaitPersonTurnResponse:
        return await self._restate_workflow_context.promise(
            self._restate_call_runtime.person_turn_promise,
            serde=runtimes.RestateAwaitPersonTurnResponseSerde(),
        ).value()
