from __future__ import annotations

import tesser.application as ts

import calls.application.ports as ports
import calls.application.relays as relays
import calls.client as client
import calls.domain as domain


class MapToCallSpec(ts.Mapper, domain.CallSpec):

    def __init__(self, place_call_request: client.PlaceCallRequest) -> None:
        super().__init__(
            person_name=place_call_request.person_name,
            phone_number=place_call_request.phone_number,
        )


class MapToConductCallRequest(ts.Mapper, relays.ConductCallRequest):

    def __init__(self, call: domain.Call) -> None:
        super().__init__(
            call_id=str(call.identity),
            person_name=str(call.person_name),
            phone_number=str(call.phone_number),
        )


class MapToPlaceCallResponse(ts.Mapper, client.PlaceCallResponse):

    def __init__(self, conduct_call_response: relays.ConductCallResponse) -> None:
        super().__init__(call_id=conduct_call_response.call_id)


class MapToLoadCallRequest(ts.Mapper, ports.LoadCallRequest):

    def __init__(self, call_id: domain.CallId) -> None:
        super().__init__(call_id=str(call_id))


class MapToCall(ts.Mapper, client.Call):

    def __init__(self, call: ports.Call) -> None:
        super().__init__(call_id=call.call_id, person_name=call.person_name)


class MapToGetCallResponse(ts.Mapper, client.GetCallResponse):

    def __init__(self, load_call_response: ports.LoadCallResponse) -> None:
        super().__init__(call=MapToCall(load_call_response.calls[0]))


class CallService(ts.ApplicationService):

    def __init__(self, conduct_call_relay: relays.ConductCallRelay, call_store: ports.CallStore) -> None:
        self._conduct_call_relay = conduct_call_relay
        self._call_store = call_store

    async def place_call(self, place_call_request: client.PlaceCallRequest) -> client.PlaceCallResponse:
        call = domain.Call(MapToCallSpec(place_call_request))
        conduct_call_response = await self._conduct_call_relay.run_conduct_call(MapToConductCallRequest(call))
        return MapToPlaceCallResponse(conduct_call_response)

    async def get_call(self, get_call_request: client.GetCallRequest) -> client.GetCallResponse:
        call_id = domain.CallId(get_call_request.call_id)
        async with self._call_store.transaction() as call_repository:
            load_call_response = await call_repository.load_call(MapToLoadCallRequest(call_id))
        return MapToGetCallResponse(load_call_response)
