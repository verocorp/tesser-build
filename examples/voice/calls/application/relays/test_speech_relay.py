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


@ts.helper
def speak_turn_response(
    call_id: str = "c1", text: str = "nice to meet you, Ada", person_name: str = "Ada"
) -> relays.SpeakTurnResponse:
    return relays.SpeakTurnResponse(call_id=call_id, text=text)


class TestSpeakTurnRequestSnapshot:
    def test_a_request_is_the_calls_snapshot(self) -> None:
        raw = relays.SpeakTurnRequestSnapshot().serialize(relays.SpeakTurnRequest(call=domain.Call(call_spec())))

        assert raw == (
            b'{"call_id": "c1", "person": {"name": "Ada", "phone_number": "+15555550100"}, "turns": [], "step": "ask_name"}'
        )

    def test_a_request_comes_back_carrying_the_same_call(self) -> None:
        speak_turn_request_snapshot = relays.SpeakTurnRequestSnapshot()
        speak_turn_request = relays.SpeakTurnRequest(call=domain.Call(call_spec(call_id="c7")))

        returned = speak_turn_request_snapshot.deserialize(speak_turn_request_snapshot.serialize(speak_turn_request))

        assert returned.call.identity == domain.CallId("c7")
        assert returned.call.conversation == speak_turn_request.call.conversation

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.SpeakTurnRequestSnapshot().deserialize(raw)


class TestSpeakTurnResponseSnapshot:
    def test_a_response_is_its_call_id_text_and_person_names(self) -> None:
        raw = relays.SpeakTurnResponseSnapshot().serialize(speak_turn_response())

        assert raw == b'{"call_id": "c1", "text": "nice to meet you, Ada"}'

    def test_a_response_comes_back_equal(self) -> None:
        speak_turn_response_snapshot = relays.SpeakTurnResponseSnapshot()

        assert (
            speak_turn_response_snapshot.deserialize(speak_turn_response_snapshot.serialize(speak_turn_response()))
            == speak_turn_response()
        )

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b"{}",
            b'{"call_id": "c1", "text": 1}',
            b'["c1"]',
        ):
            with pytest.raises(errors.DomainError):
                relays.SpeakTurnResponseSnapshot().deserialize(raw)
