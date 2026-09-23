from __future__ import annotations

import tesser.application as ts

import calls.application.ports as ports
import calls.application.relays as relays


class MapToDialPersonRequest(ts.Mapper, ports.DialPersonRequest):

    def __init__(self, dial_person_request: relays.DialPersonRequest) -> None:
        super().__init__(call_id=str(dial_person_request.call.identity))


class MapToDialPersonResponse(ts.Mapper, relays.DialPersonResponse):

    def __init__(self, dial_person_response: ports.DialPersonResponse) -> None:
        super().__init__(call_id=dial_person_response.call_id)


class MapToHangUpRequest(ts.Mapper, ports.HangUpRequest):

    def __init__(self, hang_up_request: relays.HangUpRequest) -> None:
        super().__init__(call_id=str(hang_up_request.call.identity))


class MapToHangUpResponse(ts.Mapper, relays.HangUpResponse):

    def __init__(self, hang_up_response: ports.HangUpResponse) -> None:
        super().__init__(call_id=hang_up_response.call_id)


class DialingActions(ts.Actions):

    def __init__(self, dialing: ports.Dialing) -> None:
        self._dialing = dialing

    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        dial_person_response = await self._dialing.dial_person(MapToDialPersonRequest(dial_person_request))
        return MapToDialPersonResponse(dial_person_response)

    async def hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        hang_up_response = await self._dialing.hang_up(MapToHangUpRequest(hang_up_request))
        return MapToHangUpResponse(hang_up_response)
