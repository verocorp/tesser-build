from __future__ import annotations

import tesser.testing as ts

import calls.application as application
import calls.application.ports as ports
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeDialing(ports.Dialing):

    def __init__(self) -> None:
        self.dialed: list[ports.DialPersonRequest] = []
        self.hung_up: list[ports.HangUpRequest] = []

    async def dial_person(self, dial_person_request: ports.DialPersonRequest) -> ports.DialPersonResponse:
        self.dialed.append(dial_person_request)
        return ports.DialPersonResponse(call_id=dial_person_request.call_id)

    async def hang_up(self, hang_up_request: ports.HangUpRequest) -> ports.HangUpResponse:
        self.hung_up.append(hang_up_request)
        return ports.HangUpResponse(call_id=hang_up_request.call_id)


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "Ada") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestDialingActions:

    async def test_dialing_hands_the_port_the_call_id_it_dials_for(self) -> None:
        fake_dialing = FakeDialing()
        dialing_actions = application.DialingActions(fake_dialing)

        await dialing_actions.dial_person(relays.DialPersonRequest(call=domain.Call(call_spec(call_id="c7"))))

        assert [dialed.call_id for dialed in fake_dialing.dialed] == ["c7"]

    async def test_dialing_answers_the_call_id_it_dialed_for(self) -> None:
        dialing_actions = application.DialingActions(FakeDialing())

        dial_person_response = await dialing_actions.dial_person(
            relays.DialPersonRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert dial_person_response.call_id == "c7"

    async def test_hanging_up_hands_the_port_the_call_id(self) -> None:
        fake_dialing = FakeDialing()
        dialing_actions = application.DialingActions(fake_dialing)

        await dialing_actions.hang_up(relays.HangUpRequest(call=domain.Call(call_spec(call_id="c7"))))

        assert [hung_up.call_id for hung_up in fake_dialing.hung_up] == ["c7"]

    async def test_hanging_up_answers_the_call_id_it_hung_up(self) -> None:
        dialing_actions = application.DialingActions(FakeDialing())

        hang_up_response = await dialing_actions.hang_up(relays.HangUpRequest(call=domain.Call(call_spec(call_id="c7"))))

        assert hang_up_response.call_id == "c7"
