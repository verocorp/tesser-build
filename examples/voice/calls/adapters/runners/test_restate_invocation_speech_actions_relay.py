from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.runners as runners
import calls.application.relays as relays


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self, answer: bytes) -> None:
        self._answer = answer
        self.called: list[tuple[str, str, bytes]] = []

    async def generic_call(self, service: str, handler: str, arg: bytes) -> bytes:
        self.called.append((service, handler, arg))
        return self._answer


class TestRestateInvocationSpeechActionsRelay:
    async def test_running_say_utterance_calls_the_speech_actions_service_by_name(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.SayUtteranceResponseSnapshot().serialize(relays.SayUtteranceResponse(call_id="c1"))
        )
        say_utterance_request = relays.SayUtteranceRequest(call_id="c1", text="Hello.")

        await runners.RestateInvocationSpeechActionsRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).run_say_utterance(say_utterance_request)

        assert fake_restate_workflow_context.called == [
            ("SpeechActions", "say_utterance", relays.SayUtteranceRequestSnapshot().serialize(say_utterance_request))
        ]
