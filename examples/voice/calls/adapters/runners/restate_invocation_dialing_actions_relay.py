from __future__ import annotations

import tesser.adapters as ts
import restate

import calls.application.relays as relays


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
