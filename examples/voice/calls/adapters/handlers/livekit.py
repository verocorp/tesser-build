from __future__ import annotations

import typing

import tesser.adapters as ts
import livekit.agents as livekit_agents
import livekit.agents.llm as livekit_llm
import livekit.agents.utils.participant as livekit_participant
import livekit.agents.voice.room_io as livekit_room_io
import livekit.rtc as livekit_rtc

import calls.client as client

SAY_METHOD: typing.Final[str] = "say"
_PERSON_IDENTITY: typing.Final[str] = "person"
_SPEECH_IDENTITY: typing.Final[str] = "speech"
_FOREIGN_CALLER: typing.Final[str] = "only this call's speech participant may ask the agent to say something"


class CallAgent(livekit_agents.Agent, ts.Handler):  # tesser:debt TB052
    def __init__(self, calls_client: client.CallsClient, call_id: str) -> None:
        super().__init__(instructions="")
        self._calls_client = calls_client
        self._call_id = call_id

    async def on_user_turn_completed(
        self, turn_ctx: livekit_llm.ChatContext, new_message: livekit_llm.ChatMessage
    ) -> None:
        text = new_message.text_content or ""
        if text.strip():
            await self._calls_client.person_turn_completed(
                client.PersonTurnCompletedRequest(call_id=self._call_id, text=text)
            )
        raise livekit_llm.StopResponse()

    async def say(self, rpc_invocation_data: livekit_rtc.RpcInvocationData) -> str:
        if rpc_invocation_data.caller_identity != f"{_SPEECH_IDENTITY}-{self._call_id}":
            raise livekit_rtc.RpcError(livekit_rtc.RpcError.ErrorCode.APPLICATION_ERROR, _FOREIGN_CALLER)
        speak_utterance_response = await self._calls_client.speak_utterance(
            client.SpeakUtteranceRequest(call_id=self._call_id, text=rpc_invocation_data.payload)
        )
        await self.session.say(speak_utterance_response.text)
        return ""


class LivekitHandler(ts.Handler):
    def __init__(self, calls_client: client.CallsClient, agent_name: str, stt: str, tts: str) -> None:
        self._calls_client = calls_client
        self._agent_name = agent_name
        self._stt = stt
        self._tts = tts

    async def accept_job(self, job_request: livekit_agents.JobRequest) -> None:
        await self._calls_client.attend_call(client.AttendCallRequest(call_id=job_request.room.name))
        await job_request.accept(identity=self._agent_name)

    async def start_job(self, job_context: livekit_agents.JobContext) -> None:
        await job_context.connect()
        call_id = job_context.room.name
        call_agent = CallAgent(self._calls_client, call_id)
        agent_session: livekit_agents.AgentSession[None] = livekit_agents.AgentSession(
            stt=self._stt, tts=self._tts, aec_warmup_duration=None
        )
        job_context.room.local_participant.register_rpc_method(SAY_METHOD, call_agent.say)
        await agent_session.start(
            agent=call_agent,
            room=job_context.room,
            room_options=livekit_room_io.RoomOptions(participant_identity=_PERSON_IDENTITY),
        )
        await livekit_participant.wait_for_participant(job_context.room, identity=_PERSON_IDENTITY)
        await self._calls_client.person_joined(client.PersonJoinedRequest(call_id=call_id))
