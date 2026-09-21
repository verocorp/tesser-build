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
    def __init__(self, url: str, api_key: str, api_secret: str, agent_name: str, name: str, answers: str) -> None:
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self.name = name
        self._agent_name = agent_name
        self._answers = answers
        self.room_name = ""
        self.heard: list[str] = []
        self.said: list[str] = []
        self.events: list[tuple[str, str]] = []
        self.dropped = asyncio.Event()
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

    async def join(self, room_name: str) -> None:
        self.room_name = room_name
        token = (
            livekit_api.AccessToken(self._api_key, self._api_secret)
            .with_identity("person")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            .to_jwt()
        )
        self._room.register_text_stream_handler("lk.transcription", self.on_transcription)  # tesser:debt TB051
        self._room.on("disconnected", self.on_disconnected)  # tesser:debt TB051
        await self._room.connect(self._url, token)
        await self._room.local_participant.publish_track(
            livekit_rtc.LocalAudioTrack.create_audio_track("voice", self._source),
            livekit_rtc.TrackPublishOptions(source=livekit_rtc.TrackSource.SOURCE_MICROPHONE),
        )
        self._conversation = asyncio.create_task(self.converse())  # tesser:debt TB051

    def on_disconnected(self, reason: livekit_rtc.DisconnectReason.ValueType) -> None:
        self.events.append(("dropped", livekit_rtc.DisconnectReason.Name(reason)))
        self.dropped.set()

    def on_transcription(self, reader: livekit_rtc.TextStreamReader, participant_identity: str) -> None:
        if participant_identity != self._agent_name:
            return
        reading = asyncio.ensure_future(self.read_transcription(reader))  # tesser:debt TB051
        self._readings.add(reading)

    async def read_transcription(self, reader: livekit_rtc.TextStreamReader) -> None:
        chunks: list[str] = []
        async for chunk in reader:
            if not chunks and self._answers == "over_the_question" and not self.said:
                self._inbox.put_nowait(chunk)
            chunks.append(chunk)
        text = "".join(chunks)
        if not text.strip():
            return
        self.heard.append(text)
        self.events.append(("heard", text))
        if self._answers == "when_asked":
            self._inbox.put_nowait(text)

    async def converse(self) -> None:
        while True:
            heard = await self._inbox.get()
            await self.say(await self.reply(heard))  # tesser:debt TB051

    async def reply(self, heard: str) -> str:
        if self._answers == "over_the_question":
            return f"My name is {self.name}."
        return await self.think(heard)  # tesser:debt TB051

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
class ServedApp:  # tesser:debt TB072
    def __init__(self) -> None:
        self.url = os.environ["LIVEKIT_URL"]
        self.api_key = os.environ["LIVEKIT_API_KEY"]
        self.api_secret = os.environ["LIVEKIT_API_SECRET"]
        self.agent_name = os.environ["LIVEKIT_AGENT_NAME"]
        self.voice_app = app.load()
        self._livekit_app = srv_livekit.LivekitApp(self.voice_app.calls.livekit_call_runtime)
        self._loop = asyncio.get_running_loop()
        self._people: asyncio.Queue[SimulatedPerson] = asyncio.Queue()
        self._registered = asyncio.Event()
        self._agent_server = livekit_agents.AgentServer(
            job_executor_type=livekit_agents.JobExecutorType.THREAD,
            ws_url=self.url,
            api_key=self.api_key,
            api_secret=self.api_secret,
            port=0,
        )
        self._agent_server.rtc_session(
            self.start_job, agent_name=self.agent_name, on_request=self._livekit_app.accept_job  # tesser:debt TB051
        )
        self._agent_server.on("worker_registered", self.on_worker_registered)  # tesser:debt TB051
        self._serving: asyncio.Task[None] | None = None

    def on_worker_registered(self, worker_id: str, server_info: object) -> None:
        self._registered.set()

    async def join_person(self, room_name: str) -> None:
        person = await self._people.get()
        await person.join(room_name)

    async def start_job(self, job_context: livekit_agents.JobContext) -> None:
        await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(self.join_person(job_context.room.name), self._loop)  # tesser:debt TB051
        )
        await self._livekit_app.start_job(job_context)

    async def open(self) -> None:
        await self.voice_app.open()
        self._serving = asyncio.create_task(self._agent_server.run())
        await asyncio.wait_for(self._registered.wait(), 30.0)

    def person(self, name: str, answers: str) -> SimulatedPerson:
        return SimulatedPerson(self.url, self.api_key, self.api_secret, self.agent_name, name, answers)

    async def call(self, person: SimulatedPerson) -> tuple[calls_client.PlaceCallResponse, calls_client.GetCallResponse]:
        self._people.put_nowait(person)
        try:
            place_call_response = await asyncio.wait_for(
                self.voice_app.calls.client.place_call(calls_client.PlaceCallRequest(phone_number="")), 180.0
            )
            await asyncio.wait_for(person.dropped.wait(), 30.0)
            get_call_response = await self.voice_app.calls.client.get_call(
                calls_client.GetCallRequest(call_id=place_call_response.call_id)
            )
        finally:
            await person.leave()
        return place_call_response, get_call_response

    async def close(self) -> None:
        await self._agent_server.aclose()
        if self._serving is not None:
            await asyncio.gather(self._serving, return_exceptions=True)
        await self.voice_app.close()


class TestTakePersonName:
    async def test_the_agent_asks_hears_and_greets_the_person_by_the_name_it_heard(self) -> None:
        if os.environ.get("VOICE_EVALS") != "1":
            pytest.skip("set VOICE_EVALS=1 and run scripts/verify voice with LiveKit credentials, Postgres and Restate")
        served_app = ServedApp()  # tesser:debt TB085
        await served_app.open()
        try:
            for person_name in ("Sarah", "David", "Michael"):
                person = served_app.person(person_name, "when_asked")

                place_call_response, get_call_response = await served_app.call(person)

                assert person.room_name == place_call_response.call_id
                assert get_call_response.call.person_name == person_name
                assert person.heard, person.said
                assert person_name.casefold() in person.heard[-1].casefold(), person.heard
        finally:
            await served_app.close()

    async def test_the_person_hears_the_whole_goodbye_before_the_line_drops(self) -> None:
        if os.environ.get("VOICE_EVALS") != "1":
            pytest.skip("set VOICE_EVALS=1 and run scripts/verify voice with LiveKit credentials, Postgres and Restate")
        served_app = ServedApp()  # tesser:debt TB085
        await served_app.open()
        try:
            person = served_app.person("Sarah", "when_asked")

            await served_app.call(person)

            heard_at = [at for at, (kind, _) in enumerate(person.events) if kind == "heard"]
            dropped_at = [at for at, (kind, _) in enumerate(person.events) if kind == "dropped"]
            assert heard_at and dropped_at, person.events
            assert heard_at[-1] < dropped_at[0], person.events
            assert "sarah" in person.events[heard_at[-1]][1].casefold(), person.events
            assert person.events[dropped_at[0]][1] == "ROOM_DELETED", person.events
        finally:
            await served_app.close()

    async def test_an_answer_spoken_over_the_question_is_not_lost(self) -> None:
        if os.environ.get("VOICE_EVALS") != "1":
            pytest.skip("set VOICE_EVALS=1 and run scripts/verify voice with LiveKit credentials, Postgres and Restate")
        served_app = ServedApp()  # tesser:debt TB085
        await served_app.open()
        try:
            person = served_app.person("Sarah", "over_the_question")

            _, get_call_response = await served_app.call(person)

            assert person.said == ["My name is Sarah."], person.said
            assert get_call_response.call.person_name == "Sarah"
            assert "sarah" in person.heard[-1].casefold(), person.heard
        finally:
            await served_app.close()
