from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestPersonAnsweredRequestSnapshot:
    def test_a_request_is_its_call_id(self) -> None:
        raw = relays.PersonAnsweredRequestSnapshot().serialize(relays.PersonAnsweredRequest(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_request_comes_back_equal(self) -> None:
        person_answered_request_snapshot = relays.PersonAnsweredRequestSnapshot()
        person_answered_request = relays.PersonAnsweredRequest(call_id="c1")

        returned = person_answered_request_snapshot.deserialize(
            person_answered_request_snapshot.serialize(person_answered_request)
        )

        assert returned == person_answered_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonAnsweredRequestSnapshot().deserialize(raw)


class TestPersonAnsweredResponseSnapshot:
    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.PersonAnsweredResponseSnapshot().serialize(relays.PersonAnsweredResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        person_answered_response_snapshot = relays.PersonAnsweredResponseSnapshot()
        person_answered_response = relays.PersonAnsweredResponse(call_id="c1")

        returned = person_answered_response_snapshot.deserialize(
            person_answered_response_snapshot.serialize(person_answered_response)
        )

        assert returned == person_answered_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonAnsweredResponseSnapshot().deserialize(raw)


class TestPersonInputRequestSnapshot:
    def test_a_request_is_its_call_id_and_text(self) -> None:
        raw = relays.PersonInputRequestSnapshot().serialize(
            relays.PersonInputRequest(kind=relays.INPUT_TURN_COMPLETED, call_id="c1", text="my name is Ada")
        )

        assert raw == b'{"call_id": "c1", "kind": "turn_completed", "text": "my name is Ada"}'

    def test_a_request_comes_back_equal(self) -> None:
        person_input_request_snapshot = relays.PersonInputRequestSnapshot()
        person_input_request = relays.PersonInputRequest(
            kind=relays.INPUT_TURN_COMPLETED, call_id="c1", text="my name is Ada"
        )

        returned = person_input_request_snapshot.deserialize(
            person_input_request_snapshot.serialize(person_input_request)
        )

        assert returned == person_input_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": "c1"}', b'{"call_id": "c1", "text": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonInputRequestSnapshot().deserialize(raw)


class TestPersonInputResponseSnapshot:
    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.PersonInputResponseSnapshot().serialize(relays.PersonInputResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        person_input_response_snapshot = relays.PersonInputResponseSnapshot()
        person_input_response = relays.PersonInputResponse(call_id="c1")

        returned = person_input_response_snapshot.deserialize(
            person_input_response_snapshot.serialize(person_input_response)
        )

        assert returned == person_input_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonInputResponseSnapshot().deserialize(raw)
