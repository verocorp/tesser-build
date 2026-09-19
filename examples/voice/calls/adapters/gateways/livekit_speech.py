from __future__ import annotations

import json
import typing

import tesser.adapters as ts
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc

import calls.application.ports as ports

SPEAK_TURN_METHOD: typing.Final[str] = "speak_turn"
_RESPONSE_TIMEOUT_SECONDS: typing.Final[float] = 60.0
_SPEECH_IDENTITY: typing.Final[str] = "speech"


class MapToSpeakTurnResponse(ts.Mapper, ports.SpeakTurnResponse):
    def __init__(self, call_id: str, reply: str) -> None:
        items = json.loads(reply)
        said: list[str] = []
        for item in items if isinstance(items, list) else ():
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message" and isinstance(item.get("text"), str):
                said.append(item["text"])
        super().__init__(call_id=call_id, text=" ".join(said))


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
        await room.connect(self._url, token)
        try:
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

    async def speak_turn(self, speak_turn_request: ports.SpeakTurnRequest) -> ports.SpeakTurnResponse:
        payload = json.dumps(
            {
                "persona": speak_turn_request.persona,
                "turns": [{"spoken_by": turn.spoken_by.value, "text": turn.text} for turn in speak_turn_request.turns],
                "instructions": speak_turn_request.instructions,
                "tools": [],
            }
        )
        reply = await self._livekit_agent_rpc.ask(speak_turn_request.call_id, SPEAK_TURN_METHOD, payload)
        return MapToSpeakTurnResponse(speak_turn_request.call_id, reply)
