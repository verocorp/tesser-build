from __future__ import annotations

import asyncio
import pytest
import livekit.agents.llm as livekit_llm

import tesser.testing as ts
import livekit.agents as livekit_agents
import livekit.agents.job as livekit_job
import livekit.protocol.agent as livekit_agent

import calls.adapters.runtimes as runtimes
import calls.application.client as client
import calls.application.relays as relays


@ts.fake
class FakeCallEventsRelay(relays.CallEventsRelay):
    def __init__(self) -> None:
        self.answered: list[relays.PersonAnsweredRequest] = []
        self.uttered: list[relays.PersonInputRequest] = []

    async def run_person_answered(
        self, person_answered_request: relays.PersonAnsweredRequest
    ) -> relays.PersonAnsweredResponse:
        self.answered.append(person_answered_request)
        return relays.PersonAnsweredResponse(call_id=person_answered_request.call_id)

    async def run_person_input(self, person_input_request: relays.PersonInputRequest) -> relays.PersonInputResponse:
        self.uttered.append(person_input_request)
        return relays.PersonInputResponse(call_id=person_input_request.call_id)


@ts.fake
class FakeCallEventsApplicationClient(client.CallEventsApplicationClient):
    def __init__(self) -> None:
        self.completed: list[client.UserTurnCompletedRequest] = []
        self.states: list[client.UserStateChangedRequest] = []
        self.order: list[str] = []

    async def user_turn_completed(
        self, user_turn_completed_request: client.UserTurnCompletedRequest
    ) -> client.UserTurnCompletedResponse:
        self.completed.append(user_turn_completed_request)
        self.order.append("completed")
        return client.UserTurnCompletedResponse(call_id=user_turn_completed_request.call_id)

    async def user_state_changed(
        self, user_state_changed_request: client.UserStateChangedRequest
    ) -> client.UserStateChangedResponse:
        await asyncio.sleep(0)
        self.states.append(user_state_changed_request)
        self.order.append("state")
        return client.UserStateChangedResponse(call_id=user_state_changed_request.call_id)


class TestLivekitCallRuntime:
    async def test_a_job_is_accepted_with_the_configured_agent_identity(self) -> None:
        accepted: asyncio.Queue[livekit_job.JobAcceptArguments] = asyncio.Queue()
        rejected: asyncio.Queue[bool] = asyncio.Queue()
        job_request = livekit_agents.JobRequest(
            job=livekit_agent.Job(id="job-7"), on_accept=accepted.put, on_reject=rejected.put
        )
        livekit_call_runtime = runtimes.LivekitCallRuntime(
            FakeCallEventsRelay(), FakeCallEventsApplicationClient(), "caller", "stt", "llm", "tts"
        )

        await livekit_call_runtime.accept_job(job_request)

        assert accepted.get_nowait().identity == "caller"
        assert rejected.empty()


class TestCallAgent:
    async def test_completed_message_is_delivered_unchanged_and_automatic_reply_is_stopped(self) -> None:
        fake_call_events_application_client = FakeCallEventsApplicationClient()
        call_agent = runtimes.CallAgent(fake_call_events_application_client, "c7")
        chat_message = livekit_llm.ChatMessage(role="user", content=["  my name is Grace "])

        with pytest.raises(livekit_llm.StopResponse):
            await call_agent.on_user_turn_completed(livekit_llm.ChatContext.empty(), chat_message)

        assert fake_call_events_application_client.completed[0].message is chat_message
        assert fake_call_events_application_client.completed[0].call_id == "c7"

    async def test_speech_start_is_delivered_before_its_completed_turn(self) -> None:
        fake_call_events_application_client = FakeCallEventsApplicationClient()
        call_agent = runtimes.CallAgent(fake_call_events_application_client, "c7")
        user_state_changed_event = livekit_agents.UserStateChangedEvent(old_state="listening", new_state="speaking")
        call_agent.on_user_state_changed(user_state_changed_event)

        with pytest.raises(livekit_llm.StopResponse):
            await call_agent.on_user_turn_completed(
                livekit_llm.ChatContext.empty(), livekit_llm.ChatMessage(role="user", content=["Grace"])
            )

        assert fake_call_events_application_client.states[0].event is user_state_changed_event
        assert fake_call_events_application_client.order == ["state", "completed"]

    async def test_a_tool_call_is_acknowledged_and_nothing_else(self) -> None:
        call_agent = runtimes.CallAgent(FakeCallEventsApplicationClient(), "c7")
        assert await call_agent.acknowledge({"name": "Grace"}) == "recorded"
