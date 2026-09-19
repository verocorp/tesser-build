from __future__ import annotations

import asyncio

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
        self.uttered: list[relays.PersonUtteranceRequest] = []

    async def run_person_answered(
        self, person_answered_request: relays.PersonAnsweredRequest
    ) -> relays.PersonAnsweredResponse:
        self.answered.append(person_answered_request)
        return relays.PersonAnsweredResponse(call_id=person_answered_request.call_id)

    async def run_person_utterance(
        self, person_utterance_request: relays.PersonUtteranceRequest
    ) -> relays.PersonUtteranceResponse:
        self.uttered.append(person_utterance_request)
        return relays.PersonUtteranceResponse(call_id=person_utterance_request.call_id)


@ts.fake
class FakeCallEventsApplicationClient(client.CallEventsApplicationClient):

    def __init__(self) -> None:
        self.uttered: list[relays.PersonUtteranceRequest] = []

    async def person_utterance(
        self, person_utterance_request: relays.PersonUtteranceRequest
    ) -> relays.PersonUtteranceResponse:
        self.uttered.append(person_utterance_request)
        return relays.PersonUtteranceResponse(call_id=person_utterance_request.call_id)


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

    async def test_a_final_transcript_reaches_the_application_client_without_normalization(self) -> None:
        fake_call_events_application_client = FakeCallEventsApplicationClient()
        call_agent = runtimes.CallAgent(fake_call_events_application_client, "c7")

        call_agent.on_user_input_transcribed(
            livekit_agents.UserInputTranscribedEvent(transcript="  my name is Grace \n", is_final=True)
        )
        await asyncio.sleep(0)

        assert [(uttered.call_id, uttered.text) for uttered in fake_call_events_application_client.uttered] == [
            ("c7", "  my name is Grace \n")
        ]

    async def test_an_interim_transcript_is_not_routed(self) -> None:
        fake_call_events_application_client = FakeCallEventsApplicationClient()
        call_agent = runtimes.CallAgent(fake_call_events_application_client, "c7")

        call_agent.on_user_input_transcribed(livekit_agents.UserInputTranscribedEvent(transcript="my na", is_final=False))
        await asyncio.sleep(0)

        assert fake_call_events_application_client.uttered == []

    async def test_a_tool_call_is_acknowledged_and_nothing_else(self) -> None:
        call_agent = runtimes.CallAgent(FakeCallEventsApplicationClient(), "c7")

        acknowledged = await call_agent.acknowledge({"name": "Grace"})

        assert acknowledged == "recorded"
