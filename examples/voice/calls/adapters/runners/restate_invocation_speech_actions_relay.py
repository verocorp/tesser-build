from __future__ import annotations

import tesser.adapters as ts
import restate

import calls.application.relays as relays


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
