from __future__ import annotations

import json
import typing

import tesser.adapters as ts
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc

import calls.application.ports as ports

SPEAK_TURN_METHOD: typing.Final[str] = "speak_turn"
END_PERSON_TURN_METHOD: typing.Final[str] = "end_person_turn"
PERSON_GAVE_NAME_TOOL: typing.Final[str] = "person_gave_name"
_PERSON_GAVE_NAME_SCHEMA: typing.Final[dict[str, object]] = {
    "name": PERSON_GAVE_NAME_TOOL,
    "description": "Record the name the person on the call gave for themselves.",
    "parameters": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "the person's name as they said it"}},
        "required": ["name"],
    },
}
_RESPONSE_TIMEOUT_SECONDS: typing.Final[float] = 60.0
_SPEECH_IDENTITY: typing.Final[str] = "speech"


class MapToSpeakTurnResponse(ts.Mapper, ports.SpeakTurnResponse):

    def __init__(self, call_id: str, reply: str) -> None:
        items = json.loads(reply)
        said: list[str] = []
        names: list[str] = []
        for item in items if isinstance(items, list) else ():
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message" and isinstance(item.get("text"), str):
                said.append(item["text"])
            if item.get("type") == "function_call" and item.get("name") == PERSON_GAVE_NAME_TOOL:
                raw_arguments = item.get("arguments")
                try:
                    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else None
                except json.JSONDecodeError:
                    arguments = None
                if isinstance(arguments, dict) and isinstance(arguments.get("name"), str):
                    names.append(arguments["name"])
        super().__init__(call_id=call_id, text=" ".join(said), person_names=tuple(names))


class MapToEndPersonTurnResponse(ts.Mapper, ports.EndPersonTurnResponse):

    def __init__(self, end_person_turn_request: ports.EndPersonTurnRequest) -> None:
        super().__init__(call_id=end_person_turn_request.call_id)


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
                "turns": [
                    {"spoken_by": turn.spoken_by.value, "text": turn.text} for turn in speak_turn_request.turns
                ],
                "instructions": speak_turn_request.instructions,
                "tools": [_PERSON_GAVE_NAME_SCHEMA],
            }
        )
        reply = await self._livekit_agent_rpc.ask(speak_turn_request.call_id, SPEAK_TURN_METHOD, payload)
        return MapToSpeakTurnResponse(speak_turn_request.call_id, reply)

    async def end_person_turn(
        self, end_person_turn_request: ports.EndPersonTurnRequest
    ) -> ports.EndPersonTurnResponse:
        await self._livekit_agent_rpc.ask(
            end_person_turn_request.call_id,
            END_PERSON_TURN_METHOD,
            json.dumps({"call_id": end_person_turn_request.call_id}),
        )
        return MapToEndPersonTurnResponse(end_person_turn_request)
