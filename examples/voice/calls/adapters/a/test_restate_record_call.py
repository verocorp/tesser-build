from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.a as a
import calls.application.client as client
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeCallApplicationClient(client.CallApplicationClient):
    def __init__(self) -> None:
        self.recorded: list[relays.RecordCallRequest] = []

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        self.recorded.append(record_call_request)
        return relays.RecordCallResponse(call_id=str(record_call_request.call.identity))


class TestRestateRecordCall:
    def test_it_registers_its_handler_under_the_operation_on_the_service_it_is_handed(self) -> None:
        call_actions_service = restate.Service("CallActions")

        a.RestateRecordCall(call_actions_service, FakeCallApplicationClient())

        assert sorted(call_actions_service.handlers) == ["record_call"]

    async def test_the_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_call_application_client = FakeCallApplicationClient()
        record_call_request = relays.RecordCallRequest(
            call=domain.Call(domain.CallSpec(call_id="c7", person_name="Grace"))
        )

        await a.RestateRecordCall(restate.Service("CallActions"), fake_call_application_client).handler(
            typing.cast(restate.Context, None), record_call_request
        )

        assert fake_call_application_client.recorded == [record_call_request]

