from __future__ import annotations

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.application.relays as relays


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
