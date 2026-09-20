from __future__ import annotations

import asyncio
import os

import aiohttp
import pytest
import livekit.agents as livekit_agents
import livekit.agents.inference as livekit_inference
import livekit.agents.llm as livekit_llm
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc
import tesser.testing as ts

import app as app
import calls.client as calls_client
import srv.livekit as srv_livekit

@ts.fake
class SimulatedPerson:  # tesser:debt TB072
    def __init__(self, url: str, api_key: str, api_secret: str, agent_name: str, name: str) -> None:
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self.name = name
        self._agent_name = agent_name
        self.room_name = ""
        self.heard: list[str] = []
        self._inbox: asyncio.Queue[str] = asyncio.Queue()
        self._conversation: asyncio.Task[None] | None = None
        self._llm = livekit_inference.LLM("openai/gpt-4.1-mini", api_key=api_key, api_secret=api_secret)
        self._http_session = aiohttp.ClientSession()
        self._tts = livekit_inference.TTS(
            "cartesia/sonic-2", api_key=api_key, api_secret=api_secret, http_session=self._http_session
        )
        self._source = livekit_rtc.AudioSource(self._tts.sample_rate, self._tts.num_channels)
        self._room = livekit_rtc.Room()
        self._chat_context = livekit_llm.ChatContext.empty()
        self._chat_context.add_message(
            role="system",
            content=(
                f"You are {name}, and you just answered a call. Reply with one short spoken sentence. "
                "Give your name only if the caller asks for it; until then, answer without saying your name."
            ),
        )
        self._readings: set[asyncio.Task[None]] = set()
        self.said: list[str] = []

    async def join(self, room_name: str) -> None:
        self.room_name = room_name
        token = (
            livekit_api.AccessToken(self._api_key, self._api_secret)
            .with_identity("person")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            .to_jwt()
        )
        self._room.register_text_stream_handler("lk.transcription", self.on_transcription)  # tesser:debt TB051
        await self._room.connect(self._url, token)
        await self._room.local_participant.publish_track(
            livekit_rtc.LocalAudioTrack.create_audio_track("voice", self._source),
            livekit_rtc.TrackPublishOptions(source=livekit_rtc.TrackSource.SOURCE_MICROPHONE),
        )
        self._conversation = asyncio.create_task(self.converse())  # tesser:debt TB051

    def on_transcription(self, reader: livekit_rtc.TextStreamReader, participant_identity: str) -> None:
        if participant_identity != self._agent_name:
            return
        reading = asyncio.ensure_future(self.read_transcription(reader))  # tesser:debt TB051
        self._readings.add(reading)

    async def read_transcription(self, reader: livekit_rtc.TextStreamReader) -> None:
        text = await reader.read_all()
        if text.strip():
            self.heard.append(text)
            self._inbox.put_nowait(text)

    async def converse(self) -> None:
        while True:
            heard = await self._inbox.get()
            await self.say(await self.think(heard))  # tesser:debt TB051

    async def think(self, heard: str) -> str:
        self._chat_context.add_message(role="user", content=heard)
        parts: list[str] = []
        async with self._llm.chat(chat_ctx=self._chat_context) as stream:
            async for chunk in stream:
                if chunk.delta is not None and chunk.delta.content:
                    parts.append(chunk.delta.content)
        said = "".join(parts).strip()
        self._chat_context.add_message(role="assistant", content=said)
        return said

    async def say(self, text: str) -> None:
        self.said.append(text)
        async with self._tts.synthesize(text) as stream:
            async for synthesized in stream:
                await self._source.capture_frame(synthesized.frame)
        samples_per_frame = int(self._tts.sample_rate * 0.02)
        for _ in range(int(1.5 / 0.02)):
            await self._source.capture_frame(
                livekit_rtc.AudioFrame.create(self._tts.sample_rate, self._tts.num_channels, samples_per_frame)
            )
        await self._source.wait_for_playout()

    async def leave(self) -> None:
        try:
            if self._conversation is not None:
                self._conversation.cancel()
                try:
                    await self._conversation
                except asyncio.CancelledError:
                    pass
        finally:
            await self._room.disconnect()
            try:
                await asyncio.gather(*self._readings)
            finally:
                await self._source.aclose()
                await self._llm.aclose()
                await self._tts.aclose()
                await self._http_session.close()


@ts.fake
class ParticipantHost:  # tesser:debt TB072
    def __init__(self, livekit_app: srv_livekit.LivekitApp, loop: asyncio.AbstractEventLoop) -> None:
        self._livekit_app = livekit_app
        self._loop = loop
        self.people: asyncio.Queue[SimulatedPerson] = asyncio.Queue()
        self.registered = asyncio.Event()

    def on_worker_registered(self, worker_id: str, server_info: object) -> None:
        self.registered.set()

    async def join_person(self, room_name: str) -> None:
        person = await self.people.get()
        await person.join(room_name)

    async def start_job(self, job_context: livekit_agents.JobContext) -> None:
        await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(self.join_person(job_context.room.name), self._loop)  # tesser:debt TB051
        )
        await self._livekit_app.start_job(job_context)


class TestTakePersonName:
    async def test_the_loaded_app_saves_the_name_and_the_person_hears_it_back(self) -> None:
        if os.environ.get("VOICE_EVALS") != "1":
            pytest.skip("set VOICE_EVALS=1 and run scripts/verify voice with LiveKit credentials, Postgres and Restate")
        url = os.environ["LIVEKIT_URL"]
        api_key = os.environ["LIVEKIT_API_KEY"]
        api_secret = os.environ["LIVEKIT_API_SECRET"]
        agent_name = os.environ["LIVEKIT_AGENT_NAME"]
        voice_app = app.load()
        await voice_app.open()
        livekit_app = srv_livekit.LivekitApp(voice_app.calls.livekit_call_runtime)
        participant_host = ParticipantHost(livekit_app, asyncio.get_running_loop())  # tesser:debt TB085
        agent_server = livekit_agents.AgentServer(
            job_executor_type=livekit_agents.JobExecutorType.THREAD,
            ws_url=url,
            api_key=api_key,
            api_secret=api_secret,
            port=0,
        )
        agent_server.rtc_session(
            participant_host.start_job, agent_name=agent_name, on_request=livekit_app.accept_job
        )
        agent_server.on("worker_registered", participant_host.on_worker_registered)
        serving = asyncio.create_task(agent_server.run())
        try:
            await asyncio.wait_for(participant_host.registered.wait(), 30.0)
            for person_name in ("Sarah", "David", "Michael"):
                simulated_person = SimulatedPerson(url, api_key, api_secret, agent_name, person_name)  # tesser:debt TB085
                participant_host.people.put_nowait(simulated_person)
                try:
                    place_call_response = await asyncio.wait_for(
                        voice_app.calls.client.place_call(calls_client.PlaceCallRequest(phone_number="")), 180.0
                    )
                    get_call_response = await voice_app.calls.client.get_call(
                        calls_client.GetCallRequest(call_id=place_call_response.call_id)
                    )
                finally:
                    await simulated_person.leave()

                assert simulated_person.room_name == place_call_response.call_id
                assert get_call_response.call.person_name == person_name
                assert simulated_person.heard, simulated_person.said
                assert person_name.casefold() in simulated_person.heard[-1].casefold(), simulated_person.heard
        finally:
            await agent_server.aclose()
            await asyncio.gather(serving, return_exceptions=True)
            await voice_app.close()
