from __future__ import annotations

import asyncio

import tesser.testing as ts
import livekit.agents as livekit_agents

import calls.adapters.handlers as handlers
import calls.client as client
import protocol


@ts.fake
class FakeCallsClient(client.CallsClient):

    def __init__(self) -> None:
        self.answered: list[client.ReportPersonAnsweredRequest] = []
        self.uttered: list[client.ReportPersonUtteranceRequest] = []

    async def place_call(self, place_call_request: client.PlaceCallRequest) -> client.PlaceCallResponse:
        return client.PlaceCallResponse(call_id="c1")

    async def get_call(self, get_call_request: client.GetCallRequest) -> client.GetCallResponse:
        return client.GetCallResponse(call=client.Call(call_id=get_call_request.call_id, person_name="Ada"))

    async def report_person_answered(
        self, report_person_answered_request: client.ReportPersonAnsweredRequest
    ) -> client.ReportPersonAnsweredResponse:
        self.answered.append(report_person_answered_request)
        return client.ReportPersonAnsweredResponse(call_id=report_person_answered_request.call_id)

    async def report_person_utterance(
        self, report_person_utterance_request: client.ReportPersonUtteranceRequest
    ) -> client.ReportPersonUtteranceResponse:
        self.uttered.append(report_person_utterance_request)
        return client.ReportPersonUtteranceResponse(call_id=report_person_utterance_request.call_id)


@ts.fake
class FakeJobRequest(protocol.JobRequest):

    def __init__(self) -> None:
        self.identity = ""

    async def accept(self, *, identity: str) -> None:
        self.identity = identity


class TestLivekitHandler:

    async def test_a_job_is_accepted_with_the_configured_agent_identity(self) -> None:
        fake_job_request = FakeJobRequest()
        livekit_handler = handlers.LivekitHandler(FakeCallsClient(), "caller", "stt", "llm", "tts")

        await livekit_handler.handle_accept_job_request(protocol.VoiceAcceptJobRequest(fake_job_request))

        assert fake_job_request.identity == "caller"


class TestCallAgent:

    async def test_a_final_transcript_is_routed_out_as_the_persons_utterance(self) -> None:
        fake_calls_client = FakeCallsClient()
        call_agent = handlers.CallAgent(fake_calls_client, "c7")

        call_agent.on_user_input_transcribed(
            livekit_agents.UserInputTranscribedEvent(transcript="my name is Grace", is_final=True)
        )
        await asyncio.sleep(0)

        assert [(uttered.call_id, uttered.text) for uttered in fake_calls_client.uttered] == [
            ("c7", "my name is Grace")
        ]

    async def test_an_interim_transcript_is_not_routed(self) -> None:
        fake_calls_client = FakeCallsClient()
        call_agent = handlers.CallAgent(fake_calls_client, "c7")

        call_agent.on_user_input_transcribed(livekit_agents.UserInputTranscribedEvent(transcript="my na", is_final=False))
        await asyncio.sleep(0)

        assert fake_calls_client.uttered == []

    async def test_a_tool_call_is_acknowledged_and_nothing_else(self) -> None:
        call_agent = handlers.CallAgent(FakeCallsClient(), "c7")

        acknowledged = await call_agent.acknowledge({"name": "Grace"})

        assert acknowledged == "recorded"
