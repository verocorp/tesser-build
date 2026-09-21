from __future__ import annotations

import typing

import tesser.adapters as ts
import livekit.agents as livekit_agents
import livekit.agents.llm as livekit_llm
import livekit.agents.utils.participant as livekit_participant
import livekit.agents.voice.room_io as livekit_room_io
import livekit.rtc as livekit_rtc

import calls.application.client as client
import calls.application.relays as relays

SAY_METHOD: typing.Final[str] = "say"
_PERSON_IDENTITY: typing.Final[str] = "person"


class CallAgent(livekit_agents.Agent, ts.Runtime):  # tesser:debt TB052
    def __init__(self, call_events_application_client: client.CallEventsApplicationClient, call_id: str) -> None:
        super().__init__(instructions="")
        self._call_events_application_client = call_events_application_client
        self._call_id = call_id

    async def on_user_turn_completed(  # tesser:debt TB085
        self, turn_ctx: livekit_llm.ChatContext, new_message: livekit_llm.ChatMessage
    ) -> None:
        await self._call_events_application_client.person_turn_completed(
            relays.PersonTurnCompletedRequest(call_id=self._call_id, text=new_message.text_content or "")
        )
        raise livekit_llm.StopResponse()

    async def say(self, rpc_invocation_data: livekit_rtc.RpcInvocationData) -> str:  # tesser:debt TB085
        await self.session.say(rpc_invocation_data.payload)
        return ""


class LivekitCallRuntime(ts.Runtime):
    def __init__(
        self,
        call_events_application_client: client.CallEventsApplicationClient,
        agent_name: str,
        stt: str,
        tts: str,
    ) -> None:
        self._call_events_application_client = call_events_application_client
        self._agent_name = agent_name
        self._stt = stt
        self._tts = tts

    async def accept_job(self, job_request: livekit_agents.JobRequest) -> None:  # tesser:debt TB085
        await job_request.accept(identity=self._agent_name)

    async def start_job(self, job_context: livekit_agents.JobContext) -> None:  # tesser:debt TB085
        await job_context.connect()
        call_id = job_context.room.name
        call_agent = CallAgent(self._call_events_application_client, call_id)
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
        await self._call_events_application_client.person_joined(relays.PersonJoinedRequest(call_id=call_id))
