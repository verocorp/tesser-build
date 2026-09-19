from __future__ import annotations

import pytest

import tesser.testing as ts

import calls.application.relays as relays
import calls.domain as domain
import tesser.errors as errors


@ts.helper
def call_spec(call_id: str = "c1", name: str = "Ada", phone_number: str = "+15555550100") -> domain.CallSpec:
    return domain.CallSpec(
        call_id=call_id, person=domain.PersonSpec(name=name, phone_number=phone_number), turns=(), step="ask_name"
    )


class TestInterpretTurnRequestSnapshot:
    def test_a_request_is_the_calls_snapshot(self) -> None:
        raw = relays.InterpretTurnRequestSnapshot().serialize(
            relays.InterpretTurnRequest(call=domain.Call(call_spec()))
        )

        assert raw == (
            b'{"call_id": "c1", "person": {"name": "Ada", "phone_number": "+15555550100"}, "turns": [], "step": "ask_name"}'
        )

    def test_a_request_comes_back_carrying_the_same_call(self) -> None:
        interpret_turn_request_snapshot = relays.InterpretTurnRequestSnapshot()
        interpret_turn_request = relays.InterpretTurnRequest(call=domain.Call(call_spec(call_id="c7")))

        returned = interpret_turn_request_snapshot.deserialize(
            interpret_turn_request_snapshot.serialize(interpret_turn_request)
        )

        assert returned.call.identity == domain.CallId("c7")
        assert returned.call.person == interpret_turn_request.call.person

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.InterpretTurnRequestSnapshot().deserialize(raw)


class TestInterpretTurnResponseSnapshot:
    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.InterpretTurnResponseSnapshot().serialize(
            relays.InterpretTurnResponse(call_id="c1", person_names=("Grace",))
        )

        assert raw == b'{"call_id": "c1", "person_names": ["Grace"]}'

    def test_a_response_comes_back_equal(self) -> None:
        interpret_turn_response_snapshot = relays.InterpretTurnResponseSnapshot()
        interpret_turn_response = relays.InterpretTurnResponse(call_id="c1", person_names=("Grace",))

        returned = interpret_turn_response_snapshot.deserialize(
            interpret_turn_response_snapshot.serialize(interpret_turn_response)
        )

        assert returned == interpret_turn_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.InterpretTurnResponseSnapshot().deserialize(raw)
