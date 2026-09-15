from __future__ import annotations

import asyncio
import json

import tesser.testing as ts
import livekit.agents as livekit_agents
import livekit.agents.llm as livekit_llm

import protocol
import srv.livekit as livekit


@ts.fake
class FakePersonEvents(protocol.PersonEvents):

    def __init__(self) -> None:
        self.answered: list[protocol.PersonAnswered] = []
        self.uttered: list[protocol.PersonUtterance] = []

    async def person_answered(self, person_answered: protocol.PersonAnswered) -> None:
        self.answered.append(person_answered)

    async def person_utterance(self, person_utterance: protocol.PersonUtterance) -> None:
        self.uttered.append(person_utterance)


class TestCallAgent:

    async def test_a_final_transcript_is_routed_out_as_the_persons_utterance(self) -> None:
        fake_person_events = FakePersonEvents()
        call_agent = livekit.CallAgent(fake_person_events, "c7")

        call_agent.on_user_input_transcribed(
            livekit_agents.UserInputTranscribedEvent(transcript="my name is Grace", is_final=True)
        )
        await asyncio.sleep(0)

        assert [(uttered.call_id, uttered.text) for uttered in fake_person_events.uttered] == [
            ("c7", "my name is Grace")
        ]

    async def test_an_interim_transcript_is_not_routed(self) -> None:
        fake_person_events = FakePersonEvents()
        call_agent = livekit.CallAgent(fake_person_events, "c7")

        call_agent.on_user_input_transcribed(livekit_agents.UserInputTranscribedEvent(transcript="my na", is_final=False))
        await asyncio.sleep(0)

        assert fake_person_events.uttered == []

    def test_the_chat_context_is_the_persona_then_the_turns_in_their_roles(self) -> None:
        call_agent = livekit.CallAgent(FakePersonEvents(), "c7")

        chat_context = call_agent.chat_context(
            "a friendly receptionist",
            [{"spoken_by": "agent", "text": "hi, may I have your name?"}, {"spoken_by": "person", "text": "Grace"}],
        )

        assert [
            (item.role, item.text_content) for item in chat_context.items if isinstance(item, livekit_llm.ChatMessage)
        ] == [
            ("system", "a friendly receptionist"),
            ("assistant", "hi, may I have your name?"),
            ("user", "Grace"),
        ]

    def test_the_turns_chat_items_are_encoded_in_the_order_they_happened(self) -> None:
        call_agent = livekit.CallAgent(FakePersonEvents(), "c7")
        chat_items: list[livekit_llm.ChatItem] = [
            livekit_llm.FunctionCall(call_id="call_1", name="person_gave_name", arguments='{"name": "Grace"}', created_at=2.0),
            livekit_llm.FunctionCallOutput(
                call_id="call_1", name="person_gave_name", output="recorded", is_error=False, created_at=3.0
            ),
            livekit_llm.ChatMessage(role="assistant", content=["nice to meet you, Grace"], created_at=4.0),
            livekit_llm.ChatMessage(role="assistant", content=["one moment"], created_at=1.0),
        ]

        encoded = json.loads(call_agent.encode(chat_items))

        assert encoded == [
            {"type": "message", "text": "one moment"},
            {"type": "function_call", "name": "person_gave_name", "arguments": '{"name": "Grace"}'},
            {"type": "function_call_output", "name": "person_gave_name", "output": "recorded"},
            {"type": "message", "text": "nice to meet you, Grace"},
        ]

    async def test_a_tool_call_is_acknowledged_and_nothing_else(self) -> None:
        call_agent = livekit.CallAgent(FakePersonEvents(), "c7")

        acknowledged = await call_agent.acknowledge({"name": "Grace"})

        assert acknowledged == "recorded"


class TestCallWorker:

    async def test_the_session_generates_no_reply_of_its_own(self) -> None:
        call_worker = livekit.CallWorker(
            FakePersonEvents(), "caller", "deepgram/nova-3", "openai/gpt-4.1-mini", "cartesia/sonic-2"
        )

        agent_session = call_worker.agent_session()

        assert agent_session.turn_detection == "manual"

    def test_the_session_listens_to_the_person_and_nobody_else(self) -> None:
        call_worker = livekit.CallWorker(
            FakePersonEvents(), "caller", "deepgram/nova-3", "openai/gpt-4.1-mini", "cartesia/sonic-2"
        )

        room_options = call_worker.room_options()

        assert room_options.participant_identity == "person"
