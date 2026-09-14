from __future__ import annotations

import tesser.application as ts

import calls.application.relays as relays


class MapToRecordCallRequest(ts.Mapper, relays.RecordCallRequest):

    def __init__(self, place_call_request: relays.PlaceCallRequest) -> None:
        super().__init__(
            call_id=place_call_request.call_id,
            person_name=place_call_request.person_name,
            phone_number=place_call_request.phone_number,
        )


class MapToPlaceCallResponse(ts.Mapper, relays.PlaceCallResponse):

    def __init__(self, record_call_response: relays.RecordCallResponse) -> None:
        super().__init__(call_id=record_call_response.call_id)


class CallOrchestrator(ts.Orchestrator):

    def __init__(self, call_actions_runner: relays.CallActionsRunner) -> None:
        self._call_actions_runner = call_actions_runner

    async def place_call(self, place_call_request: relays.PlaceCallRequest) -> relays.PlaceCallResponse:
        record_call_response = await self._call_actions_runner.run_record_call(
            MapToRecordCallRequest(place_call_request)
        )
        return MapToPlaceCallResponse(record_call_response)
