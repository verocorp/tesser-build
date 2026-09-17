from __future__ import annotations

import tesser.adapters as ts
import restate

import calls.adapters.runtimes as runtimes
import calls.application.relays as relays


class RestateInvocationDialingRelay(ts.Runner):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_call_runtime: runtimes.RestateCallRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_call_runtime = restate_call_runtime

    async def run_dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        return await self._restate_workflow_context.service_call(
            self._restate_call_runtime.dial_person_handler, dial_person_request
        )

    async def run_hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        return await self._restate_workflow_context.service_call(
            self._restate_call_runtime.hang_up_handler, hang_up_request
        )
