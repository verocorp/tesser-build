from __future__ import annotations

import typing

import tesser.adapters as ts
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc

import calls.application.ports as ports

SAY_METHOD: typing.Final[str] = "say"
_RESPONSE_TIMEOUT_SECONDS: typing.Final[float] = 60.0
_SPEECH_IDENTITY: typing.Final[str] = "speech"


class LivekitAgentRpc(ts.Gateway):
    def __init__(
        self,
        room_type: type[livekit_rtc.Room],
        url: str,
        api_key: str,
        api_secret: str,
        agent_identity: str,
    ) -> None:
        self._room_type = room_type
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self._agent_identity = agent_identity

    async def ask(self, call_id: str, method: str, payload: str) -> str:
        token = (
            livekit_api.AccessToken(self._api_key, self._api_secret)
            .with_identity(f"{_SPEECH_IDENTITY}-{call_id}")
            .with_grants(
                livekit_api.VideoGrants(
                    room_join=True,
                    room=call_id,
                    can_publish=False,
                    can_subscribe=False,
                    can_publish_data=True,
                )
            )
            .to_jwt()
        )
        room = self._room_type()  # tesser:debt TB085
        try:
            await room.connect(self._url, token)
            return await room.local_participant.perform_rpc(
                destination_identity=self._agent_identity,
                method=method,
                payload=payload,
                response_timeout=_RESPONSE_TIMEOUT_SECONDS,
            )
        finally:
            await room.disconnect()


class LivekitSpeech(ts.Gateway):
    def __init__(self, livekit_agent_rpc: LivekitAgentRpc) -> None:
        self._livekit_agent_rpc = livekit_agent_rpc

    async def say_utterance(self, say_utterance_request: ports.SayUtteranceRequest) -> ports.SayUtteranceResponse:
        await self._livekit_agent_rpc.ask(say_utterance_request.call_id, SAY_METHOD, say_utterance_request.text)
        return ports.SayUtteranceResponse(call_id=say_utterance_request.call_id)
