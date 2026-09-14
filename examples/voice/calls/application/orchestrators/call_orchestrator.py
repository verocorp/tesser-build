from __future__ import annotations

import tesser.application as ts

import calls.application.relays as relays


class MapToRecordCallRequest(ts.Mapper, relays.RecordCallRequest):

    def __init__(self, conduct_call_request: relays.ConductCallRequest) -> None:
        super().__init__(
            call_id=conduct_call_request.call_id,
            person_name=conduct_call_request.person_name,
            phone_number=conduct_call_request.phone_number,
        )


class MapToConductCallResponse(ts.Mapper, relays.ConductCallResponse):

    def __init__(self, record_call_response: relays.RecordCallResponse) -> None:
        super().__init__(call_id=record_call_response.call_id)


class CallOrchestrator(ts.Orchestrator):

    def __init__(self, record_call_relay: relays.RecordCallRelay) -> None:
        self._record_call_relay = record_call_relay

    async def conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        record_call_response = await self._record_call_relay.run_record_call(
            MapToRecordCallRequest(conduct_call_request)
        )
        return MapToConductCallResponse(record_call_response)
