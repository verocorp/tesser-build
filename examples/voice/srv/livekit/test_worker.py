from __future__ import annotations

import asyncio

import tesser.testing as ts
import livekit.agents as livekit_agents

import protocol
import srv.livekit as livekit


@ts.fake
class FakeCallEvents(protocol.CallEvents):

    def __init__(self) -> None:
        self.answered: list[protocol.PersonAnswered] = []
        self.uttered: list[protocol.PersonUtterance] = []

    async def person_answered(self, person_answered: protocol.PersonAnswered) -> None:
        self.answered.append(person_answered)

    async def person_utterance(self, person_utterance: protocol.PersonUtterance) -> None:
        self.uttered.append(person_utterance)


class TestCallAgent:

    async def test_a_final_transcript_is_routed_out_as_the_persons_utterance(self) -> None:
        fake_call_events = FakeCallEvents()
        call_agent = livekit.CallAgent(fake_call_events, "c7")

        call_agent.on_user_input_transcribed(
            livekit_agents.UserInputTranscribedEvent(transcript="my name is Grace", is_final=True)
        )
        await asyncio.sleep(0)

        assert [(uttered.call_id, uttered.text) for uttered in fake_call_events.uttered] == [
            ("c7", "my name is Grace")
        ]

    async def test_an_interim_transcript_is_not_routed(self) -> None:
        fake_call_events = FakeCallEvents()
        call_agent = livekit.CallAgent(fake_call_events, "c7")

        call_agent.on_user_input_transcribed(livekit_agents.UserInputTranscribedEvent(transcript="my na", is_final=False))
        await asyncio.sleep(0)

        assert fake_call_events.uttered == []

    async def test_a_tool_call_is_acknowledged_and_nothing_else(self) -> None:
        call_agent = livekit.CallAgent(FakeCallEvents(), "c7")

        acknowledged = await call_agent.acknowledge({"name": "Grace"})

        assert acknowledged == "recorded"
