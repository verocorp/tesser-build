from __future__ import annotations

import tesser.adapters as ts
import livekit.api as livekit_api

import calls.application.ports as ports


class LivekitDialing(ts.Gateway):

    def __init__(
        self,
        livekit_api_type: type[livekit_api.LiveKitAPI],
        url: str,
        api_key: str,
        api_secret: str,
        agent_name: str,
    ) -> None:
        self._livekit_api_type = livekit_api_type
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self._agent_name = agent_name

    async def dial_person(self, dial_person_request: ports.DialPersonRequest) -> ports.DialPersonResponse:
        livekit = self._livekit_api_type(self._url, self._api_key, self._api_secret)  # tesser:debt TB085
        try:
            await livekit.agent_dispatch.create_dispatch(
                livekit_api.CreateAgentDispatchRequest(agent_name=self._agent_name, room=dial_person_request.call_id)
            )
        finally:
            await livekit.aclose()
        return ports.DialPersonResponse(call_id=dial_person_request.call_id)

    async def hang_up(self, hang_up_request: ports.HangUpRequest) -> ports.HangUpResponse:
        livekit = self._livekit_api_type(self._url, self._api_key, self._api_secret)  # tesser:debt TB085
        try:
            await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=hang_up_request.call_id))
        finally:
            await livekit.aclose()
        return ports.HangUpResponse(call_id=hang_up_request.call_id)
