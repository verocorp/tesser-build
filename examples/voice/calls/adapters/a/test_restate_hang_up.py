from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.a as a
import calls.application.client as client
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeDialingApplicationClient(client.DialingApplicationClient):
    def __init__(self) -> None:
        self.hung_up: list[relays.HangUpRequest] = []

    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))

    async def hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        self.hung_up.append(hang_up_request)
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


class TestRestateHangUp:
    def test_it_registers_its_handler_under_the_operation_on_the_service_it_is_handed(self) -> None:
        dialing_actions_service = restate.Service("DialingActions")

        a.RestateHangUp(dialing_actions_service, FakeDialingApplicationClient())

        assert sorted(dialing_actions_service.handlers) == ["hang_up"]

    async def test_the_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_dialing_application_client = FakeDialingApplicationClient()
        hang_up_request = relays.HangUpRequest(
            call=domain.Call(domain.CallSpec(call_id="c7", person_name=""))
        )

        await a.RestateHangUp(restate.Service("DialingActions"), fake_dialing_application_client).handler(
            typing.cast(restate.Context, None), hang_up_request
        )

        assert fake_dialing_application_client.hung_up == [hang_up_request]

