from __future__ import annotations

import calls.application as application
import calls.client as client


class TestAgentService:
    async def test_a_call_is_attended_under_its_call_id(self) -> None:
        agent_service = application.AgentService()

        attend_call_response = await agent_service.attend_call(
            client.AttendCallRequest(call_id="c7")
        )

        assert attend_call_response.call_id == "c7"

    async def test_an_utterance_is_spoken_under_its_call_id(self) -> None:
        agent_service = application.AgentService()

        speak_utterance_response = await agent_service.speak_utterance(
            client.SpeakUtteranceRequest(call_id="c7", text="Hello.")
        )

        assert (speak_utterance_response.call_id, speak_utterance_response.text) == ("c7", "Hello.")
