from __future__ import annotations

import asyncio

import pytest
import tesser.testing as ts
import livekit.agents as livekit_agents
import livekit.agents.job as livekit_job
import livekit.agents.llm as livekit_llm
import livekit.protocol.agent as livekit_agent
import livekit.protocol.models as livekit_models
import livekit.rtc as livekit_rtc

import calls.adapters.handlers as handlers
import calls.client as client


@ts.fake
class FakeCallsClient(client.CallsClient):
    def __init__(self) -> None:
        self.joined: list[client.PersonJoinedRequest] = []
        self.completed: list[client.PersonTurnCompletedRequest] = []
        self.attended: list[client.AttendCallRequest] = []
        self.spoken: list[client.SpeakUtteranceRequest] = []

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

    async def attend_call(self, attend_call_request: client.AttendCallRequest) -> client.AttendCallResponse:
        self.attended.append(attend_call_request)
        return client.AttendCallResponse(call_id=attend_call_request.call_id)

    async def speak_utterance(
        self, speak_utterance_request: client.SpeakUtteranceRequest
    ) -> client.SpeakUtteranceResponse:
        self.spoken.append(speak_utterance_request)
        return client.SpeakUtteranceResponse(call_id=speak_utterance_request.call_id, text=speak_utterance_request.text)


class TestLivekitHandler:
    async def test_a_job_is_accepted_with_the_configured_agent_identity(self) -> None:
        accepted: asyncio.Queue[livekit_job.JobAcceptArguments] = asyncio.Queue()
        rejected: asyncio.Queue[bool] = asyncio.Queue()
        job_request = livekit_agents.JobRequest(
            job=livekit_agent.Job(id="job-7", room=livekit_models.Room(name="c7")),
            on_accept=accepted.put,
            on_reject=rejected.put,
        )
        livekit_handler = handlers.LivekitHandler(FakeCallsClient(), "caller", "stt", "tts")

        await livekit_handler.accept_job(job_request)

        assert accepted.get_nowait().identity == "caller"
        assert rejected.empty()

    async def test_a_job_asks_the_client_to_attend_the_call_its_room_is_named_for(self) -> None:
        accepted: asyncio.Queue[livekit_job.JobAcceptArguments] = asyncio.Queue()
        rejected: asyncio.Queue[bool] = asyncio.Queue()
        job_request = livekit_agents.JobRequest(
            job=livekit_agent.Job(id="job-7", room=livekit_models.Room(name="c7")),
            on_accept=accepted.put,
            on_reject=rejected.put,
        )
        fake_calls_client = FakeCallsClient()
        livekit_handler = handlers.LivekitHandler(fake_calls_client, "caller", "stt", "tts")

        await livekit_handler.accept_job(job_request)

        assert [attend_call_request.call_id for attend_call_request in fake_calls_client.attended] == ["c7"]


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

    async def test_a_turn_that_carries_no_text_is_not_reported(self) -> None:
        fake_calls_client = FakeCallsClient()
        call_agent = handlers.CallAgent(fake_calls_client, "c7")

        with pytest.raises(livekit_llm.StopResponse):
            await call_agent.on_user_turn_completed(
                livekit_llm.ChatContext.empty(), livekit_llm.ChatMessage(role="user", content=[])
            )

        assert fake_calls_client.completed == []

    async def test_a_turn_that_carries_only_whitespace_is_not_reported(self) -> None:
        fake_calls_client = FakeCallsClient()
        call_agent = handlers.CallAgent(fake_calls_client, "c7")

        with pytest.raises(livekit_llm.StopResponse):
            await call_agent.on_user_turn_completed(
                livekit_llm.ChatContext.empty(), livekit_llm.ChatMessage(role="user", content=[" \n"])
            )

        assert fake_calls_client.completed == []

    async def test_a_say_from_a_participant_that_is_not_speech_is_refused(self) -> None:
        call_agent = handlers.CallAgent(FakeCallsClient(), "c7")

        with pytest.raises(livekit_rtc.RpcError) as raised:
            await call_agent.say(
                livekit_rtc.RpcInvocationData(
                    request_id="r1", caller_identity="person", payload="Hello.", response_timeout=5.0, method="say"
                )
            )

        assert raised.value.code == livekit_rtc.RpcError.ErrorCode.APPLICATION_ERROR

    async def test_a_say_from_its_own_calls_speech_participant_asks_the_client_to_speak_the_utterance(self) -> None:
        fake_calls_client = FakeCallsClient()
        call_agent = handlers.CallAgent(fake_calls_client, "c7")

        with pytest.raises(RuntimeError, match="the agent is not running"):
            await call_agent.say(
                livekit_rtc.RpcInvocationData(
                    request_id="r1", caller_identity="speech-c7", payload="Hello.", response_timeout=5.0, method="say"
                )
            )

        assert [
            (speak_utterance_request.call_id, speak_utterance_request.text)
            for speak_utterance_request in fake_calls_client.spoken
        ] == [("c7", "Hello.")]

    async def test_a_refused_say_never_reaches_the_client(self) -> None:
        fake_calls_client = FakeCallsClient()
        call_agent = handlers.CallAgent(fake_calls_client, "c7")

        with pytest.raises(livekit_rtc.RpcError):
            await call_agent.say(
                livekit_rtc.RpcInvocationData(
                    request_id="r1", caller_identity="person", payload="Hello.", response_timeout=5.0, method="say"
                )
            )

        assert fake_calls_client.spoken == []

    async def test_a_say_from_its_own_calls_speech_participant_passes_the_check_to_the_agent_session(self) -> None:
        call_agent = handlers.CallAgent(FakeCallsClient(), "c7")

        with pytest.raises(RuntimeError, match="the agent is not running"):
            await call_agent.say(
                livekit_rtc.RpcInvocationData(
                    request_id="r1", caller_identity="speech-c7", payload="Hello.", response_timeout=5.0, method="say"
                )
            )

    async def test_a_say_from_another_calls_speech_participant_is_refused(self) -> None:
        call_agent = handlers.CallAgent(FakeCallsClient(), "c7")

        with pytest.raises(livekit_rtc.RpcError) as raised:
            await call_agent.say(
                livekit_rtc.RpcInvocationData(
                    request_id="r1", caller_identity="speech-c8", payload="Hello.", response_timeout=5.0, method="say"
                )
            )

        assert raised.value.code == livekit_rtc.RpcError.ErrorCode.APPLICATION_ERROR
