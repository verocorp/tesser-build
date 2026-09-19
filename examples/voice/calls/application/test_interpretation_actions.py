from __future__ import annotations

import tesser.testing as ts
import calls.application as application
import calls.application.ports as ports
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeInterpretation(ports.Interpretation):
    def __init__(self) -> None:
        self.requests: list[ports.InterpretTurnRequest] = []

    async def interpret_turn(self, interpret_turn_request: ports.InterpretTurnRequest) -> ports.InterpretTurnResponse:
        self.requests.append(interpret_turn_request)
        return ports.InterpretTurnResponse(call_id=interpret_turn_request.call_id, person_names=("Grace",))


class TestInterpretationActions:
    async def test_listening_receives_its_own_instructions_and_the_completed_turn(self) -> None:
        call = domain.Call(
            domain.CallSpec(
                call_id="c7",
                person=domain.PersonSpec(name="", phone_number="+15555550100"),
                turns=(domain.TurnSpec(speaker="person", utterances=("my name is Grace",)),),
                step="ask_name",
            )
        )
        fake_interpretation = FakeInterpretation()

        interpret_turn_response = await application.InterpretationActions(fake_interpretation).interpret_turn(
            relays.InterpretTurnRequest(call=call)
        )

        assert fake_interpretation.requests[0].instructions == str(call.listening_instructions)
        assert fake_interpretation.requests[0].instructions != str(call.instructions)
        assert [(t.spoken_by, t.text) for t in fake_interpretation.requests[0].turns] == [
            ("person", "my name is Grace")
        ]
        assert (interpret_turn_response.call_id, interpret_turn_response.person_names) == ("c7", ("Grace",))
