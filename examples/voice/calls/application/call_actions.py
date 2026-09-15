from __future__ import annotations

import tesser.application as ts

import calls.application.ports as ports
import calls.application.relays as relays


class MapToSaveCallRequest(ts.Mapper, ports.SaveCallRequest):

    def __init__(self, record_call_request: relays.RecordCallRequest) -> None:
        call = record_call_request.call
        super().__init__(
            call_id=str(call.identity),
            person_name=str(call.person.name),
            phone_number=str(call.person.phone_number),
        )


class MapToRecordCallResponse(ts.Mapper, relays.RecordCallResponse):

    def __init__(self, save_call_response: ports.SaveCallResponse) -> None:
        super().__init__(call_id=save_call_response.call_id)


class CallActions(ts.Actions):

    def __init__(self, call_store: ports.CallStore) -> None:
        self._call_store = call_store

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        async with self._call_store.transaction() as call_repository:
            save_call_response = await call_repository.save_call(MapToSaveCallRequest(record_call_request))
        return MapToRecordCallResponse(save_call_response)
