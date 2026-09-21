from __future__ import annotations

import asyncio
import time
import typing

import aiohttp
import livekit.agents.inference as livekit_inference
import livekit.agents.llm as livekit_llm
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc

WHEN_ASKED: typing.Final[str] = "when_asked"
OVER_THE_QUESTION: typing.Final[str] = "over_the_question"
HEARD: typing.Final[str] = "heard"
DROPPED: typing.Final[str] = "dropped"
_IDENTITY: typing.Final[str] = "person"
_FIND_ROOM_SECONDS: typing.Final[float] = 60.0
_CALL_SECONDS: typing.Final[float] = 180.0
_POLL_SECONDS: typing.Final[float] = 0.5
_TRAILING_SILENCE_SECONDS: typing.Final[float] = 1.5
_FRAME_SECONDS: typing.Final[float] = 0.02


class Person:
    def __init__(self, url: str, api_key: str, api_secret: str, agent_name: str, name: str, answers: str) -> None:
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self._agent_name = agent_name
        self._answers = answers
        self.name = name
        self.room_name = ""
        self.heard: list[str] = []
        self.said: list[str] = []
        self.events: list[tuple[str, str]] = []
        self._dropped = asyncio.Event()
        self._inbox: asyncio.Queue[str] = asyncio.Queue()
        self._conversation: asyncio.Task[None] | None = None
        self._readings: set[asyncio.Task[None]] = set()
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

    async def answer(self) -> None:
        try:
            room_name = await asyncio.wait_for(self._find_room(), _FIND_ROOM_SECONDS)
            await self._join(room_name)
            await asyncio.wait_for(self._dropped.wait(), _CALL_SECONDS)
        finally:
            await self._leave()

    async def _find_room(self) -> str:
        started_at = int(time.time()) - 1
        api = livekit_api.LiveKitAPI(self._url, self._api_key, self._api_secret)
        try:
            while True:
                rooms = await api.room.list_rooms(livekit_api.ListRoomsRequest())
                for room in rooms.rooms:
                    if room.creation_time < started_at:
                        continue
                    participants = await api.room.list_participants(livekit_api.ListParticipantsRequest(room=room.name))
                    identities = {participant.identity for participant in participants.participants}
                    if self._agent_name in identities and _IDENTITY not in identities:
                        return str(room.name)
                await asyncio.sleep(_POLL_SECONDS)
        finally:
            await api.aclose()

    async def _join(self, room_name: str) -> None:
        self.room_name = room_name
        token = (
            livekit_api.AccessToken(self._api_key, self._api_secret)
            .with_identity(_IDENTITY)
            .with_grants(livekit_api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            .to_jwt()
        )
        self._room.register_text_stream_handler("lk.transcription", self._on_transcription)
        self._room.on("disconnected", self._on_disconnected)
        await self._room.connect(self._url, token)
        await self._room.local_participant.publish_track(
            livekit_rtc.LocalAudioTrack.create_audio_track("voice", self._source),
            livekit_rtc.TrackPublishOptions(source=livekit_rtc.TrackSource.SOURCE_MICROPHONE),
        )
        self._conversation = asyncio.create_task(self._converse())

    def _on_disconnected(self, reason: livekit_rtc.DisconnectReason.ValueType) -> None:
        self.events.append((DROPPED, livekit_rtc.DisconnectReason.Name(reason)))
        self._dropped.set()

    def _on_transcription(self, reader: livekit_rtc.TextStreamReader, participant_identity: str) -> None:
        if participant_identity != self._agent_name:
            return
        self._readings.add(asyncio.ensure_future(self._read_transcription(reader)))

    async def _read_transcription(self, reader: livekit_rtc.TextStreamReader) -> None:
        chunks: list[str] = []
        async for chunk in reader:
            if not chunks and self._answers == OVER_THE_QUESTION and not self.said:
                self._inbox.put_nowait(chunk)
            chunks.append(chunk)
        text = "".join(chunks)
        if not text.strip():
            return
        self.heard.append(text)
        self.events.append((HEARD, text))
        if self._answers == WHEN_ASKED:
            self._inbox.put_nowait(text)

    async def _converse(self) -> None:
        while True:
            heard = await self._inbox.get()
            if self._answers == OVER_THE_QUESTION:
                await self._say(f"My name is {self.name}.")
            else:
                await self._say(await self._think(heard))

    async def _think(self, heard: str) -> str:
        self._chat_context.add_message(role="user", content=heard)
        parts: list[str] = []
        async with self._llm.chat(chat_ctx=self._chat_context) as stream:
            async for chunk in stream:
                if chunk.delta is not None and chunk.delta.content:
                    parts.append(chunk.delta.content)
        said = "".join(parts).strip()
        self._chat_context.add_message(role="assistant", content=said)
        return said

    async def _say(self, text: str) -> None:
        self.said.append(text)
        async with self._tts.synthesize(text) as stream:
            async for synthesized in stream:
                await self._source.capture_frame(synthesized.frame)
        samples_per_frame = int(self._tts.sample_rate * _FRAME_SECONDS)
        for _ in range(int(_TRAILING_SILENCE_SECONDS / _FRAME_SECONDS)):
            await self._source.capture_frame(
                livekit_rtc.AudioFrame.create(self._tts.sample_rate, self._tts.num_channels, samples_per_frame)
            )
        await self._source.wait_for_playout()

    async def _leave(self) -> None:
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
