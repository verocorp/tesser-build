from __future__ import annotations

import tesser.adapters as ts
import restate

import calls.adapters.runtimes as runtimes
import calls.application.relays as relays


class RestateInvocationSpeechRelay(ts.Runner):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_call_runtime: runtimes.RestateCallRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_call_runtime = restate_call_runtime

    async def run_speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        return await self._restate_workflow_context.service_call(
            self._restate_call_runtime.speak_turn_handler, speak_turn_request
        )

    async def run_end_person_turn(
        self, end_person_turn_request: relays.EndPersonTurnRequest
    ) -> relays.EndPersonTurnResponse:
        return await self._restate_workflow_context.service_call(
            self._restate_call_runtime.end_person_turn_handler, end_person_turn_request
        )
