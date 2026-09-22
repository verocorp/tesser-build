from __future__ import annotations

import asyncio

import pytest
import tesser.testing as ts
import livekit.agents as livekit_agents
import livekit.agents.job as livekit_job
import livekit.agents.llm as livekit_llm
import livekit.protocol.agent as livekit_agent

import calls.adapters.handlers as handlers
import calls.client as client


@ts.fake
class FakeCallsClient(client.CallsClient):
    def __init__(self) -> None:
        self.joined: list[client.PersonJoinedRequest] = []
        self.completed: list[client.PersonTurnCompletedRequest] = []

    async def place_call(self, place_call_request: client.PlaceCallRequest) -> client.PlaceCallResponse:
        return client.PlaceCallResponse(call_id="c7")

    async def get_call(self, get_call_request: client.GetCallRequest) -> client.GetCallResponse:
        return client.GetCallResponse(call=client.Call(call_id=get_call_request.call_id, person_name=""))

    async def person_joined(self, person_joined_request: client.PersonJoinedRequest) -> client.PersonJoinedResponse:
        self.joined.append(person_joined_request)
        return client.PersonJoinedResponse(call_id=person_joined_request.call_id)

    async def person_turn_completed(
        self, person_turn_completed_request: client.PersonTurnCompletedRequest
    ) -> client.PersonTurnCompletedResponse:
        self.completed.append(person_turn_completed_request)
        return client.PersonTurnCompletedResponse(call_id=person_turn_completed_request.call_id)


class TestLivekitHandler:
    async def test_a_job_is_accepted_with_the_configured_agent_identity(self) -> None:
        accepted: asyncio.Queue[livekit_job.JobAcceptArguments] = asyncio.Queue()
        rejected: asyncio.Queue[bool] = asyncio.Queue()
        job_request = livekit_agents.JobRequest(
            job=livekit_agent.Job(id="job-7"), on_accept=accepted.put, on_reject=rejected.put
        )
        livekit_handler = handlers.LivekitHandler(FakeCallsClient(), "caller", "stt", "tts")

        await livekit_handler.accept_job(job_request)

        assert accepted.get_nowait().identity == "caller"
        assert rejected.empty()


class TestCallAgent:
    async def test_a_completed_person_turn_is_reported_as_the_call_and_what_the_person_said(self) -> None:
        fake_calls_client = FakeCallsClient()
        call_agent = handlers.CallAgent(fake_calls_client, "c7")

        with pytest.raises(livekit_llm.StopResponse):
            await call_agent.on_user_turn_completed(
                livekit_llm.ChatContext.empty(), livekit_llm.ChatMessage(role="user", content=["my name is Grace"])
            )

        assert [
            (person_turn_completed_request.call_id, person_turn_completed_request.text)
            for person_turn_completed_request in fake_calls_client.completed
        ] == [("c7", "my name is Grace")]

    async def test_a_completed_person_turn_stops_the_agents_own_reply(self) -> None:
        call_agent = handlers.CallAgent(FakeCallsClient(), "c7")

        with pytest.raises(livekit_llm.StopResponse):
            await call_agent.on_user_turn_completed(
                livekit_llm.ChatContext.empty(), livekit_llm.ChatMessage(role="user", content=["Grace"])
            )

    async def test_a_turn_that_carries_no_text_is_reported_as_nothing_said(self) -> None:
        fake_calls_client = FakeCallsClient()
        call_agent = handlers.CallAgent(fake_calls_client, "c7")

        with pytest.raises(livekit_llm.StopResponse):
            await call_agent.on_user_turn_completed(
                livekit_llm.ChatContext.empty(), livekit_llm.ChatMessage(role="user", content=[])
            )

        assert [
            person_turn_completed_request.text
            for person_turn_completed_request in fake_calls_client.completed
        ] == [""]
