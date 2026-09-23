from __future__ import annotations

import pytest

import calls.application as application
import calls.client as client


class TestAgentService:
    async def test_a_call_is_attended_under_its_call_id(self) -> None:
        agent_service = application.AgentService()

        attend_call_response = await agent_service.attend_call(
            client.AttendCallRequest(call_id="c7")
        )

        assert attend_call_response.call_id == "c7"

    async def test_an_utterance_is_spoken_as_its_trimmed_text(self) -> None:
        agent_service = application.AgentService()

        speak_utterance_response = await agent_service.speak_utterance(
            client.SpeakUtteranceRequest(
                call_id="c7", text="  Hello. Please tell me your first name.\n"
            )
        )

        assert (speak_utterance_response.call_id, speak_utterance_response.text) == (
            "c7",
            "Hello. Please tell me your first name.",
        )

    async def test_an_utterance_that_says_nothing_is_refused(self) -> None:
        agent_service = application.AgentService()

        with pytest.raises(ValueError):
            await agent_service.speak_utterance(
                client.SpeakUtteranceRequest(call_id="c7", text=" \t\n")
            )
