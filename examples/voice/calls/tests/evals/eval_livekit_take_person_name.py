from __future__ import annotations  # tesser:debt TB070

import asyncio
import os
import typing

import aiohttp
import pytest

import tesser.testing as ts
import livekit.agents as livekit_agents
import livekit.agents.inference as livekit_inference
import livekit.agents.llm as livekit_llm
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc

import calls.adapters.gateways as gateways
import calls.adapters.handlers as handlers
import calls.adapters.repositories as repositories
import calls.application as application
import calls.application.orchestrators as orchestrators
import calls.application.ports as ports
import calls.application.relays as relays
import calls.client as client
import calls.component as component
import calls.domain as domain
import pgdatabase.database as pgdatabase_database
import srv.livekit as srv_livekit

_PERSON_IDENTITY: typing.Final[str] = "person"
_SIP_CALL_STATUS: typing.Final[str] = "sip.callStatus"
_SIP_CALL_ACTIVE: typing.Final[str] = "active"
_TRANSCRIPTION_TOPIC: typing.Final[str] = "lk.transcription"
_SEGMENT_ID: typing.Final[str] = "lk.segment_id"
_PERSON_LLM: typing.Final[str] = "openai/gpt-4.1-mini"
_PERSON_TTS: typing.Final[str] = "cartesia/sonic-2"
_PERSON_INSTRUCTIONS: typing.Final[str] = (
    "You are {name}, and you just answered a phone call. Reply with one short spoken sentence. "
    "Give your name only if the caller asks for it; until then, answer what was said without saying your name."
)
_PERSON_NAMES: typing.Final[tuple[str, ...]] = ("Ada", "Grace", "Alan", "Barbara", "Edsger")
_MUST_PASS: typing.Final[int] = 4
_CALL_SECONDS: typing.Final[float] = 180.0
_REGISTRATION_SECONDS: typing.Final[float] = 30.0
_HEARING_SECONDS: typing.Final[float] = 5.0
_HEARING_POLL_SECONDS: typing.Final[float] = 0.2
_TRAILING_SILENCE_SECONDS: typing.Final[float] = 1.5
_FRAME_SECONDS: typing.Final[float] = 0.02
_DEFAULT_AGENT_NAME: typing.Final[str] = "caller-eval"
_DEFAULT_STT: typing.Final[str] = "deepgram/nova-3"
_DEFAULT_LLM: typing.Final[str] = "openai/gpt-4.1-mini"
_DEFAULT_TTS: typing.Final[str] = "cartesia/sonic-2"


@ts.fake
class SimulatedPerson:

    def __init__(self, url: str, api_key: str, api_secret: str, name: str) -> None:
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self.name = name
        self._llm = livekit_inference.LLM(_PERSON_LLM, api_key=api_key, api_secret=api_secret)
        self._http_session = aiohttp.ClientSession()
        self._tts = livekit_inference.TTS(
            _PERSON_TTS, api_key=api_key, api_secret=api_secret, http_session=self._http_session
        )
        self._source = livekit_rtc.AudioSource(self._tts.sample_rate, self._tts.num_channels)
        self._room = livekit_rtc.Room()
        self._chat_context = livekit_llm.ChatContext.empty()
        self._chat_context.add_message(role="system", content=_PERSON_INSTRUCTIONS.format(name=name))
        self._heard: dict[str, str] = {}
        self._answered: set[str] = set()
        self._readings: set[asyncio.Task[None]] = set()
        self._waited_in_vain = False
        self.said: list[str] = []

    async def join(self, room_name: str) -> None:
        token = (
            livekit_api.AccessToken(self._api_key, self._api_secret)
            .with_identity(_PERSON_IDENTITY)
            .with_grants(livekit_api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            .to_jwt()
        )
        self._room.register_text_stream_handler(_TRANSCRIPTION_TOPIC, self.on_transcription)  # tesser:debt TB051
        await self._room.connect(self._url, token)
        await self._room.local_participant.publish_track(
            livekit_rtc.LocalAudioTrack.create_audio_track("voice", self._source),
            livekit_rtc.TrackPublishOptions(source=livekit_rtc.TrackSource.SOURCE_MICROPHONE),
        )
        livekit = livekit_api.LiveKitAPI(self._url, self._api_key, self._api_secret)
        try:
            await livekit.room.update_participant(
                livekit_api.UpdateParticipantRequest(
                    room=room_name, identity=_PERSON_IDENTITY, attributes={_SIP_CALL_STATUS: _SIP_CALL_ACTIVE}
                )
            )
        finally:
            await livekit.aclose()

    def on_transcription(self, reader: livekit_rtc.TextStreamReader, participant_identity: str) -> None:
        if participant_identity == _PERSON_IDENTITY:
            return
        reading = asyncio.ensure_future(self.read_transcription(reader))  # tesser:debt TB051
        self._readings.add(reading)
        reading.add_done_callback(self._readings.discard)

    async def read_transcription(self, reader: livekit_rtc.TextStreamReader) -> None:
        text = await reader.read_all()
        attributes = reader.info.attributes or {}
        self._heard[attributes.get(_SEGMENT_ID, reader.info.stream_id)] = text

    def unanswered(self) -> str:
        return " ".join(text for segment, text in self._heard.items() if segment not in self._answered).strip()

    async def hear(self) -> str:
        heard = self.unanswered()  # tesser:debt TB051
        if not heard and not self._waited_in_vain:
            deadline = asyncio.get_running_loop().time() + _HEARING_SECONDS
            while not heard and asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(_HEARING_POLL_SECONDS)
                heard = self.unanswered()  # tesser:debt TB051
            self._waited_in_vain = not heard
        if heard:
            self._waited_in_vain = False
            self._answered.update(self._heard)
        return heard

    async def think(self, heard: str) -> str:
        self._chat_context.add_message(role="user", content=heard)
        stream = self._llm.chat(chat_ctx=self._chat_context)
        parts: list[str] = []
        async for chunk in stream:
            if chunk.delta is not None and chunk.delta.content:
                parts.append(chunk.delta.content)
        await stream.aclose()
        said = "".join(parts).strip()
        self._chat_context.add_message(role="assistant", content=said)
        return said

    async def say(self, text: str) -> None:
        self.said.append(text)
        async for synthesized in self._tts.synthesize(text):
            await self._source.capture_frame(synthesized.frame)
        samples_per_frame = int(self._tts.sample_rate * _FRAME_SECONDS)
        for _ in range(int(_TRAILING_SILENCE_SECONDS / _FRAME_SECONDS)):
            await self._source.capture_frame(
                livekit_rtc.AudioFrame.create(self._tts.sample_rate, self._tts.num_channels, samples_per_frame)
            )
        await self._source.wait_for_playout()

    async def reply(self) -> None:
        heard = await self.hear()  # tesser:debt TB051
        if not heard:
            return
        await self.say(await self.think(heard))  # tesser:debt TB051

    async def leave(self) -> None:
        await self._room.disconnect()
        await self._llm.aclose()
        await self._tts.aclose()
        await self._http_session.close()


@ts.fake
class SimulatedPersonDialing(ports.Dialing):

    def __init__(
        self, url: str, api_key: str, api_secret: str, agent_name: str, people: dict[str, SimulatedPerson]
    ) -> None:
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self._agent_name = agent_name
        self._people = people
        self.expecting: SimulatedPerson | None = None

    async def dial_person(self, dial_person_request: ports.DialPersonRequest) -> ports.DialPersonResponse:
        if self.expecting is None:
            raise RuntimeError("no simulated person is expecting this call")
        livekit = livekit_api.LiveKitAPI(self._url, self._api_key, self._api_secret)
        try:
            await livekit.agent_dispatch.create_dispatch(
                livekit_api.CreateAgentDispatchRequest(agent_name=self._agent_name, room=dial_person_request.call_id)
            )
        finally:
            await livekit.aclose()
        self._people[dial_person_request.call_id] = self.expecting
        await self.expecting.join(dial_person_request.call_id)
        self.expecting = None
        return ports.DialPersonResponse(call_id=dial_person_request.call_id)

    async def hang_up(self, hang_up_request: ports.HangUpRequest) -> ports.HangUpResponse:
        livekit = livekit_api.LiveKitAPI(self._url, self._api_key, self._api_secret)
        try:
            await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=hang_up_request.call_id))
        finally:
            await livekit.aclose()
        await self._people[hang_up_request.call_id].leave()
        return ports.HangUpResponse(call_id=hang_up_request.call_id)


@ts.fake
class InlineCallSignals(
    relays.PersonAnsweredRelay,
    relays.PersonUtteranceRelay,
    relays.AwaitPersonAnsweredRelay,
    relays.AwaitPersonUtteranceRelay,
):

    def __init__(self, loop: asyncio.AbstractEventLoop, people: dict[str, SimulatedPerson]) -> None:
        self._loop = loop
        self._people = people
        self._answered: dict[str, asyncio.Event] = {}
        self._utterances: dict[str, asyncio.Queue[str]] = {}

    def answered(self, call_id: str) -> asyncio.Event:
        return self._answered.setdefault(call_id, asyncio.Event())

    def utterances(self, call_id: str) -> asyncio.Queue[str]:
        return self._utterances.setdefault(call_id, asyncio.Queue())

    def mark_answered(self, call_id: str) -> None:
        self.answered(call_id).set()  # tesser:debt TB051

    def enqueue(self, call_id: str, text: str) -> None:
        self.utterances(call_id).put_nowait(text)  # tesser:debt TB051

    async def run_person_answered(
        self, person_answered_request: relays.PersonAnsweredRequest
    ) -> relays.PersonAnsweredResponse:
        self._loop.call_soon_threadsafe(self.mark_answered, person_answered_request.call_id)  # tesser:debt TB051
        return relays.PersonAnsweredResponse(call_id=person_answered_request.call_id)

    async def run_person_utterance(
        self, person_utterance_request: relays.PersonUtteranceRequest
    ) -> relays.PersonUtteranceResponse:
        self._loop.call_soon_threadsafe(
            self.enqueue, person_utterance_request.call_id, person_utterance_request.text  # tesser:debt TB051
        )
        return relays.PersonUtteranceResponse(call_id=person_utterance_request.call_id)

    async def await_person_answered(
        self, await_person_answered_request: relays.AwaitPersonAnsweredRequest
    ) -> relays.AwaitPersonAnsweredResponse:
        await self.answered(await_person_answered_request.call_id).wait()  # tesser:debt TB051
        return relays.AwaitPersonAnsweredResponse(call_id=await_person_answered_request.call_id)

    async def await_person_utterance(
        self, await_person_utterance_request: relays.AwaitPersonUtteranceRequest
    ) -> relays.AwaitPersonUtteranceResponse:
        call_id = await_person_utterance_request.call_id
        await self._people[call_id].reply()
        try:
            text = await asyncio.wait_for(
                self.utterances(call_id).get(), await_person_utterance_request.within_seconds  # tesser:debt TB051
            )
        except TimeoutError:
            return relays.AwaitPersonUtteranceResponse(call_id=call_id, heard=relays.HEARD_SILENCE, text="")
        return relays.AwaitPersonUtteranceResponse(call_id=call_id, heard=relays.HEARD_UTTERANCE, text=text)


@ts.fake
class InlineCallInvocations(
    relays.DialPersonRelay,
    relays.SpeakTurnRelay,
    relays.EndPersonTurnRelay,
    relays.HangUpRelay,
    relays.RecordCallRelay,
):

    def __init__(
        self,
        call_actions: application.CallActions,
        dialing_actions: application.DialingActions,
        speech_actions: application.SpeechActions,
    ) -> None:
        self._call_actions = call_actions
        self._dialing_actions = dialing_actions
        self._speech_actions = speech_actions

    async def run_dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        return await self._dialing_actions.dial_person(dial_person_request)

    async def run_speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        return await self._speech_actions.speak_turn(speak_turn_request)

    async def run_end_person_turn(
        self, end_person_turn_request: relays.EndPersonTurnRequest
    ) -> relays.EndPersonTurnResponse:
        return await self._speech_actions.end_person_turn(end_person_turn_request)

    async def run_hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        return await self._dialing_actions.hang_up(hang_up_request)

    async def run_record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        return await self._call_actions.record_call(record_call_request)


@ts.fake
class InlineConductCall(relays.ConductCallRelay):

    def __init__(  # tesser:debt TB081
        self, inline_call_invocations: InlineCallInvocations, inline_call_signals: InlineCallSignals
    ) -> None:
        self._inline_call_invocations = inline_call_invocations
        self._inline_call_signals = inline_call_signals
        self.conducted: list[domain.Call] = []

    async def run_conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        self.conducted.append(conduct_call_request.call)
        return await orchestrators.CallOrchestrator(
            self._inline_call_invocations,
            self._inline_call_signals,
            self._inline_call_invocations,
            self._inline_call_signals,
            self._inline_call_invocations,
            self._inline_call_invocations,
            self._inline_call_invocations,
        ).conduct_call(conduct_call_request)


@ts.fake
class Registration:

    def __init__(self) -> None:
        self.registered = asyncio.Event()

    def on_worker_registered(self, worker_id: str, server_info: object) -> None:
        self.registered.set()


@ts.helper
def transcript(call: domain.Call) -> list[tuple[str, str]]:
    return [(str(turn.speaker), " ".join(str(u) for u in turn.utterances)) for turn in call.conversation.turns]


@ts.helper
def last_agent_line(call: domain.Call) -> str:
    return next((text for speaker, text in reversed(transcript(call)) if speaker == "agent"), "")


class TestTakePersonName:

    async def test_the_agent_asks_for_the_persons_name_keeps_it_and_says_it_back(self) -> None:
        if os.environ.get("VOICE_EVALS") != "1":
            pytest.skip("an eval drives real LiveKit and real models: set VOICE_EVALS=1 with LIVEKIT_* credentials")
        url = os.environ["LIVEKIT_URL"]
        api_key = os.environ["LIVEKIT_API_KEY"]
        api_secret = os.environ["LIVEKIT_API_SECRET"]
        agent_name = os.environ.get("LIVEKIT_AGENT_NAME", _DEFAULT_AGENT_NAME)
        config = component.Config(
            component.Spec(
                storage=os.environ["CALLS_STORAGE"],
                ingress="",
                livekit_url=url,
                livekit_api_key=api_key,
                livekit_api_secret=api_secret,
                livekit_agent_name=agent_name,
                livekit_sip_trunk_id="",
            )
        )
        database = pgdatabase_database.Database(config.database)
        await database.open()
        people: dict[str, SimulatedPerson] = {}
        simulated_person_dialing = SimulatedPersonDialing(url, api_key, api_secret, agent_name, people)
        inline_call_signals = InlineCallSignals(asyncio.get_running_loop(), people)
        inline_conduct_call = InlineConductCall(
            InlineCallInvocations(
                application.CallActions(repositories.PostgresCallStore(database)),
                application.DialingActions(simulated_person_dialing),
                application.SpeechActions(
                    gateways.LivekitSpeech(
                        gateways.LivekitAgentRpc(livekit_rtc.Room, url, api_key, api_secret, agent_name)
                    )
                ),
            ),
            inline_call_signals,
        )
        call_service = application.CallService(
            inline_conduct_call, inline_call_signals, inline_call_signals, repositories.PostgresCallStore(database)
        )
        livekit_worker = srv_livekit.LivekitWorker(
            handlers.LivekitHandler(call_service),
            agent_name,
            os.environ.get("LIVEKIT_STT_MODEL", _DEFAULT_STT),
            os.environ.get("LIVEKIT_LLM_MODEL", _DEFAULT_LLM),
            os.environ.get("LIVEKIT_TTS_MODEL", _DEFAULT_TTS),
        )
        agent_server = livekit_agents.AgentServer(
            job_executor_type=livekit_agents.JobExecutorType.THREAD, ws_url=url, api_key=api_key, api_secret=api_secret
        )
        agent_server.rtc_session(livekit_worker.entrypoint, agent_name=agent_name, on_request=livekit_worker.on_request)
        registration = Registration()  # tesser:debt TB085
        agent_server.on("worker_registered", registration.on_worker_registered)
        serving = asyncio.ensure_future(agent_server.run())
        await asyncio.wait_for(registration.registered.wait(), _REGISTRATION_SECONDS)

        kept: list[bool] = []
        greeted: list[bool] = []
        transcripts: list[list[tuple[str, str]]] = []
        try:
            for person_name in _PERSON_NAMES:
                simulated_person = SimulatedPerson(url, api_key, api_secret, person_name)  # tesser:debt TB085
                simulated_person_dialing.expecting = simulated_person
                place_call_response = await asyncio.wait_for(
                    call_service.place_call(client.PlaceCallRequest(person_name="", phone_number="")), _CALL_SECONDS
                )
                get_call_response = await call_service.get_call(
                    client.GetCallRequest(call_id=place_call_response.call_id)
                )
                conducted = inline_conduct_call.conducted[-1]
                transcripts.append(transcript(conducted))
                print(f"\n[{person_name}] kept={get_call_response.call.person_name!r} said={simulated_person.said} heard={transcript(conducted)}")
                kept.append(get_call_response.call.person_name == person_name)
                greeted.append(person_name.lower() in last_agent_line(conducted).lower())
        finally:
            await agent_server.aclose()
            serving.cancel()
            await database.close()

        assert sum(kept) >= _MUST_PASS and sum(greeted) >= _MUST_PASS, transcripts
