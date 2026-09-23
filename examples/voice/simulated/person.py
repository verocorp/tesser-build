from __future__ import annotations

import asyncio
import logging
import time
import typing

import aiohttp
import livekit.agents.inference as livekit_inference
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
_log: typing.Final[logging.Logger] = logging.getLogger("simulated.person")


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
        self._http_session = aiohttp.ClientSession()
        self._tts = livekit_inference.TTS(
            "cartesia/sonic-2", api_key=api_key, api_secret=api_secret, http_session=self._http_session
        )
        self._source = livekit_rtc.AudioSource(self._tts.sample_rate, self._tts.num_channels)
        self._room = livekit_rtc.Room()

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
                        _log.info("%s found room %s", self.name, room.name)
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
        _log.info("%s joined %s", self.name, room_name)

    def _on_disconnected(self, reason: livekit_rtc.DisconnectReason.ValueType) -> None:
        self.events.append((DROPPED, livekit_rtc.DisconnectReason.Name(reason)))
        _log.info("%s dropped: %s", self.name, livekit_rtc.DisconnectReason.Name(reason))
        self._dropped.set()

    def _on_transcription(self, reader: livekit_rtc.TextStreamReader, participant_identity: str) -> None:
        if participant_identity != self._agent_name:
            return
        self._readings.add(asyncio.ensure_future(self._read_transcription(reader)))

    async def _read_transcription(self, reader: livekit_rtc.TextStreamReader) -> None:
        chunks: list[str] = []
        async for chunk in reader:
            _log.info("%s hears chunk %r", self.name, chunk)
            if not chunks and self._answers == OVER_THE_QUESTION and not self.said:
                self._inbox.put_nowait(chunk)
            chunks.append(chunk)
        text = "".join(chunks)
        if not text.strip():
            return
        self.heard.append(text)
        self.events.append((HEARD, text))
        if self._answers == WHEN_ASKED and not self.said:
            self._inbox.put_nowait(text)

    async def _converse(self) -> None:
        await self._inbox.get()
        await self._say(f"{self.name}.")

    async def _say(self, text: str) -> None:
        self.said.append(text)
        _log.info("%s says %r", self.name, text)
        async with self._tts.synthesize(text) as stream:
            async for synthesized in stream:
                await self._source.capture_frame(synthesized.frame)
        samples_per_frame = int(self._tts.sample_rate * _FRAME_SECONDS)
        for _ in range(int(_TRAILING_SILENCE_SECONDS / _FRAME_SECONDS)):
            await self._source.capture_frame(
                livekit_rtc.AudioFrame.create(self._tts.sample_rate, self._tts.num_channels, samples_per_frame)
            )
        await self._source.wait_for_playout()
        _log.info("%s finished saying %r", self.name, text)

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
                await self._tts.aclose()
                await self._http_session.close()
