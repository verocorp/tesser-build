from __future__ import annotations

import tesser.adapters as ts
import restate

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
