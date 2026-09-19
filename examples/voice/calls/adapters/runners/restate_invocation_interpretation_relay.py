from __future__ import annotations

import tesser.adapters as ts
import restate

import calls.adapters.runtimes as runtimes
import calls.application.relays as relays


class RestateInvocationInterpretationRelay(ts.Runner):
    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_call_runtime: runtimes.RestateCallRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_call_runtime = restate_call_runtime

    async def run_interpret_turn(
        self, interpret_turn_request: relays.InterpretTurnRequest
    ) -> relays.InterpretTurnResponse:
        return await self._restate_workflow_context.service_call(
            self._restate_call_runtime.interpret_turn_handler, interpret_turn_request
        )
