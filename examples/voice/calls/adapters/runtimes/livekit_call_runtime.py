from __future__ import annotations

import asyncio
import json
import typing

import tesser.adapters as ts
import livekit.agents as livekit_agents
import livekit.agents.llm as livekit_llm
import livekit.agents.utils.participant as livekit_participant
import livekit.agents.voice.room_io as livekit_room_io
import livekit.rtc as livekit_rtc

import calls.application.client as client
import calls.application.relays as relays

SPEAK_TURN_METHOD: typing.Final[str] = "speak_turn"
END_PERSON_TURN_METHOD: typing.Final[str] = "end_person_turn"
_PERSON_IDENTITY: typing.Final[str] = "person"
_SIP_CALL_STATUS: typing.Final[str] = "sip.callStatus"
_SIP_CALL_ACTIVE: typing.Final[str] = "active"
_ACKNOWLEDGED: typing.Final[str] = "recorded"
_AGENT_ROLE: typing.Final[str] = "agent"
_TURN_HANDLING: typing.Final[livekit_agents.TurnHandlingOptions] = {"turn_detection": "manual"}


class CallAgent(livekit_agents.Agent, ts.Runtime):  # tesser:debt TB052

    def __init__(self, call_events_application_client: client.CallEventsApplicationClient, call_id: str) -> None:
        super().__init__(instructions="")
        self._call_events_application_client = call_events_application_client
        self._call_id = call_id
        self._deliveries: set[asyncio.Task[relays.PersonUtteranceResponse]] = set()

    def on_user_input_transcribed(self, user_input_transcribed_event: livekit_agents.UserInputTranscribedEvent) -> None:  # tesser:debt TB085
        if user_input_transcribed_event.is_final:
            delivery = asyncio.ensure_future(
                self._call_events_application_client.person_utterance(
                    relays.PersonUtteranceRequest(call_id=self._call_id, text=user_input_transcribed_event.transcript)
                )
            )
            self._deliveries.add(delivery)
            delivery.add_done_callback(self._deliveries.discard)

    async def acknowledge(self, raw_arguments: dict[str, object]) -> str:  # tesser:debt TB085
        return _ACKNOWLEDGED

    def created_at(self, chat_item: livekit_llm.ChatItem) -> float:  # tesser:debt TB085
        return chat_item.created_at

    async def speak_turn(self, rpc_invocation_data: livekit_rtc.RpcInvocationData) -> str:  # tesser:debt TB085
        payload = json.loads(rpc_invocation_data.payload)
        await self.update_tools(
            [livekit_llm.function_tool(self.acknowledge, raw_schema=schema) for schema in payload["tools"]]  # tesser:debt TB051
        )
        chat_context = livekit_llm.ChatContext.empty()
        chat_context.add_message(role="system", content=payload["persona"])
        for turn in payload["turns"]:
            chat_context.add_message(
                role="assistant" if turn["spoken_by"] == _AGENT_ROLE else "user", content=turn["text"]
            )
        speech_handle = self.session.generate_reply(chat_ctx=chat_context, instructions=payload["instructions"])
        await speech_handle
        failure = speech_handle.exception()
        if failure is not None:
            raise failure
        encoded: list[dict[str, str]] = []
        for chat_item in sorted(speech_handle.chat_items, key=self.created_at):  # tesser:debt TB051
            if isinstance(chat_item, livekit_llm.ChatMessage):
                encoded.append({"type": "message", "text": chat_item.text_content or ""})
            elif isinstance(chat_item, livekit_llm.FunctionCall):
                encoded.append({"type": "function_call", "name": chat_item.name, "arguments": chat_item.arguments})
            elif isinstance(chat_item, livekit_llm.FunctionCallOutput):
                encoded.append({"type": "function_call_output", "name": chat_item.name, "output": chat_item.output})
        return json.dumps(encoded)

    async def end_person_turn(self, rpc_invocation_data: livekit_rtc.RpcInvocationData) -> str:  # tesser:debt TB085
        await self.session.commit_user_turn(skip_reply=True)
        await asyncio.gather(*self._deliveries)
        return ""


class LivekitCallRuntime(ts.Runtime):

    def __init__(  # tesser:debt TB081
        self,
        call_events_relay: relays.CallEventsRelay,
        call_events_application_client: client.CallEventsApplicationClient,
        agent_name: str,
        stt: str,
        llm: str,
        tts: str,
    ) -> None:
        self._call_events_relay = call_events_relay
        self._call_events_application_client = call_events_application_client
        self._agent_name = agent_name
        self._stt = stt
        self._llm = llm
        self._tts = tts

    async def accept_job(self, job_request: livekit_agents.JobRequest) -> None:  # tesser:debt TB085
        await job_request.accept(identity=self._agent_name)

    async def start_job(self, job_context: livekit_agents.JobContext) -> None:  # tesser:debt TB085
        await job_context.connect()
        call_id = job_context.room.name
        call_agent = CallAgent(self._call_events_application_client, call_id)
        agent_session: livekit_agents.AgentSession[None] = livekit_agents.AgentSession(
            stt=self._stt, llm=self._llm, tts=self._tts, turn_handling=_TURN_HANDLING
        )
        agent_session.on("user_input_transcribed", call_agent.on_user_input_transcribed)
        job_context.room.local_participant.register_rpc_method(SPEAK_TURN_METHOD, call_agent.speak_turn)
        job_context.room.local_participant.register_rpc_method(END_PERSON_TURN_METHOD, call_agent.end_person_turn)
        await agent_session.start(
            agent=call_agent,
            room=job_context.room,
            room_options=livekit_room_io.RoomOptions(participant_identity=_PERSON_IDENTITY),
        )
        await livekit_participant.wait_for_participant(job_context.room, identity=_PERSON_IDENTITY)
        await livekit_participant.wait_for_participant_attribute(
            job_context.room, identity=_PERSON_IDENTITY, attribute=_SIP_CALL_STATUS, value=_SIP_CALL_ACTIVE
        )
        await self._call_events_relay.run_person_answered(relays.PersonAnsweredRequest(call_id=call_id))
