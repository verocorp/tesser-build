from __future__ import annotations

import asyncio
import json
import os
import typing

import tesser.srv as ts
import livekit.agents as livekit_agents
import livekit.agents.llm as livekit_llm
import livekit.agents.utils.participant as livekit_participant
import livekit.agents.voice.room_io as livekit_room_io
import livekit.rtc as livekit_rtc

import app as app
import calls.adapters.handlers as calls_handlers
import protocol

SPEAK_TURN_METHOD: typing.Final[str] = "speak_turn"
END_PERSON_TURN_METHOD: typing.Final[str] = "end_person_turn"
_PERSON_IDENTITY: typing.Final[str] = "person"
_SIP_CALL_STATUS: typing.Final[str] = "sip.callStatus"
_SIP_CALL_ACTIVE: typing.Final[str] = "active"
_ACKNOWLEDGED: typing.Final[str] = "recorded"
_AGENT_ROLE: typing.Final[str] = "agent"
_DEFAULT_STT: typing.Final[str] = "deepgram/nova-3"
_DEFAULT_LLM: typing.Final[str] = "openai/gpt-4.1-mini"
_DEFAULT_TTS: typing.Final[str] = "cartesia/sonic-2"
_TURN_HANDLING: typing.Final[livekit_agents.TurnHandlingOptions] = {"turn_detection": "manual"}


class CallAgent(livekit_agents.Agent, ts.Host):

    def __init__(self, call_events: protocol.CallEvents, call_id: str) -> None:
        super().__init__(instructions="")
        self._call_events = call_events
        self._call_id = call_id
        self._deliveries: set[asyncio.Task[None]] = set()

    def on_user_input_transcribed(self, user_input_transcribed_event: livekit_agents.UserInputTranscribedEvent) -> None:
        if user_input_transcribed_event.is_final and user_input_transcribed_event.transcript.strip():
            delivery = asyncio.ensure_future(
                self._call_events.person_utterance(
                    protocol.PersonUtterance(call_id=self._call_id, text=user_input_transcribed_event.transcript)
                )
            )
            self._deliveries.add(delivery)
            delivery.add_done_callback(self._deliveries.discard)

    async def acknowledge(self, raw_arguments: dict[str, object]) -> str:
        return _ACKNOWLEDGED

    def chat_context(self, persona: str, turns: list[dict[str, str]]) -> livekit_llm.ChatContext:
        chat_context = livekit_llm.ChatContext.empty()
        chat_context.add_message(role="system", content=persona)
        for turn in turns:
            chat_context.add_message(
                role="assistant" if turn["spoken_by"] == _AGENT_ROLE else "user", content=turn["text"]
            )
        return chat_context

    def encode(self, chat_items: list[livekit_llm.ChatItem]) -> str:
        encoded: list[dict[str, str]] = []
        for chat_item in sorted(chat_items, key=self.created_at):  # tesser:debt TB051
            if isinstance(chat_item, livekit_llm.ChatMessage):
                encoded.append({"type": "message", "text": chat_item.text_content or ""})
            elif isinstance(chat_item, livekit_llm.FunctionCall):
                encoded.append({"type": "function_call", "name": chat_item.name, "arguments": chat_item.arguments})
            elif isinstance(chat_item, livekit_llm.FunctionCallOutput):
                encoded.append({"type": "function_call_output", "name": chat_item.name, "output": chat_item.output})
        return json.dumps(encoded)

    def created_at(self, chat_item: livekit_llm.ChatItem) -> float:
        return chat_item.created_at

    async def speak_turn(self, rpc_invocation_data: livekit_rtc.RpcInvocationData) -> str:
        payload = json.loads(rpc_invocation_data.payload)
        await self.update_tools(
            [livekit_llm.function_tool(self.acknowledge, raw_schema=schema) for schema in payload["tools"]]  # tesser:debt TB051
        )
        speech_handle = self.session.generate_reply(
            chat_ctx=self.chat_context(payload["persona"], payload["turns"]),  # tesser:debt TB051
            instructions=payload["instructions"],
        )
        await speech_handle
        failure = speech_handle.exception()
        if failure is not None:
            raise failure
        return self.encode(speech_handle.chat_items)  # tesser:debt TB051

    async def end_person_turn(self, rpc_invocation_data: livekit_rtc.RpcInvocationData) -> str:
        await self.session.commit_user_turn(skip_reply=True)
        await asyncio.gather(*self._deliveries)
        return ""


class LivekitWorker(ts.Host):

    def __init__(self, call_events: protocol.CallEvents, agent_name: str, stt: str, llm: str, tts: str) -> None:
        self._call_events = call_events
        self._agent_name = agent_name
        self._stt = stt
        self._llm = llm
        self._tts = tts

    async def on_request(self, job_request: livekit_agents.JobRequest) -> None:
        await job_request.accept(identity=self._agent_name)

    async def entrypoint(self, job_context: livekit_agents.JobContext) -> None:
        await job_context.connect()
        call_id = job_context.room.name
        call_agent = CallAgent(self._call_events, call_id)
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
        await self._call_events.person_answered(protocol.PersonAnswered(call_id=call_id))


class LivekitHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        voice_app = app.load()
        agent_name = os.environ["LIVEKIT_AGENT_NAME"]
        livekit_worker = LivekitWorker(
            calls_handlers.LivekitHandler(voice_app.calls.client),
            agent_name,
            os.environ.get("LIVEKIT_STT_MODEL", _DEFAULT_STT),
            os.environ.get("LIVEKIT_LLM_MODEL", _DEFAULT_LLM),
            os.environ.get("LIVEKIT_TTS_MODEL", _DEFAULT_TTS),
        )
        agent_server = livekit_agents.AgentServer(
            job_executor_type=livekit_agents.JobExecutorType.THREAD,
            ws_url=os.environ["LIVEKIT_URL"],
            api_key=os.environ["LIVEKIT_API_KEY"],
            api_secret=os.environ["LIVEKIT_API_SECRET"],
        )
        agent_server.rtc_session(
            livekit_worker.entrypoint, agent_name=agent_name, on_request=livekit_worker.on_request
        )
        with asyncio.Runner() as runner:
            runner.run(voice_app.open())
            try:
                runner.run(agent_server.run())
            finally:
                runner.run(voice_app.close())
        return 0


if __name__ == "__main__":
    ts.main(LivekitHost().run)
