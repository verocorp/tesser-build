from __future__ import annotations

import typing

import tesser.adapters as ts
import livekit.api as livekit_api

import calls.application.ports as ports

_PERSON_IDENTITY: typing.Final[str] = "person"


class LivekitDialing(ts.Gateway):

    def __init__(self, livekit: livekit_api.LiveKitAPI, agent_name: str, sip_trunk_id: str) -> None:
        self._livekit = livekit
        self._agent_name = agent_name
        self._sip_trunk_id = sip_trunk_id

    async def dial_person(self, dial_person_request: ports.DialPersonRequest) -> ports.DialPersonResponse:
        await self._livekit.agent_dispatch.create_dispatch(
            livekit_api.CreateAgentDispatchRequest(agent_name=self._agent_name, room=dial_person_request.call_id)
        )
        await self._livekit.sip.create_sip_participant(
            livekit_api.CreateSIPParticipantRequest(
                sip_trunk_id=self._sip_trunk_id,
                sip_call_to=dial_person_request.phone_number,
                room_name=dial_person_request.call_id,
                participant_identity=_PERSON_IDENTITY,
                wait_until_answered=False,
            )
        )
        return ports.DialPersonResponse(call_id=dial_person_request.call_id)

    async def hang_up(self, hang_up_request: ports.HangUpRequest) -> ports.HangUpResponse:
        await self._livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=hang_up_request.call_id))
        return ports.HangUpResponse(call_id=hang_up_request.call_id)
