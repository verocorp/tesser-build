from __future__ import annotations

import tesser.adapters as ts
import livekit.api as livekit_api

import calls.application.ports as ports


class LivekitDialing(ts.Gateway):

    def __init__(
        self,
        url: str,
        api_key: str,
        api_secret: str,
        agent_name: str,
    ) -> None:
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self._agent_name = agent_name

    async def dial_person(self, dial_person_request: ports.DialPersonRequest) -> ports.DialPersonResponse:
        async with livekit_api.LiveKitAPI(self._url, self._api_key, self._api_secret) as livekit:
            await livekit.agent_dispatch.create_dispatch(
                livekit_api.CreateAgentDispatchRequest(agent_name=self._agent_name, room=dial_person_request.call_id)
            )
        return ports.DialPersonResponse(call_id=dial_person_request.call_id)

    async def hang_up(self, hang_up_request: ports.HangUpRequest) -> ports.HangUpResponse:
        async with livekit_api.LiveKitAPI(self._url, self._api_key, self._api_secret) as livekit:
            await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=hang_up_request.call_id))
        return ports.HangUpResponse(call_id=hang_up_request.call_id)
