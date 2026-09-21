from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestPersonJoinedRequestSnapshot:
    def test_a_request_is_its_call_id(self) -> None:
        raw = relays.PersonJoinedRequestSnapshot().serialize(relays.PersonJoinedRequest(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_request_comes_back_equal(self) -> None:
        person_joined_request_snapshot = relays.PersonJoinedRequestSnapshot()
        person_joined_request = relays.PersonJoinedRequest(call_id="c1")

        returned = person_joined_request_snapshot.deserialize(
            person_joined_request_snapshot.serialize(person_joined_request)
        )

        assert returned == person_joined_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonJoinedRequestSnapshot().deserialize(raw)


class TestPersonJoinedResponseSnapshot:
    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.PersonJoinedResponseSnapshot().serialize(relays.PersonJoinedResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        person_joined_response_snapshot = relays.PersonJoinedResponseSnapshot()
        person_joined_response = relays.PersonJoinedResponse(call_id="c1")

        returned = person_joined_response_snapshot.deserialize(
            person_joined_response_snapshot.serialize(person_joined_response)
        )

        assert returned == person_joined_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonJoinedResponseSnapshot().deserialize(raw)


class TestPersonTurnCompletedRequestSnapshot:
    def test_a_request_is_its_call_id_and_the_text_the_person_said(self) -> None:
        raw = relays.PersonTurnCompletedRequestSnapshot().serialize(
            relays.PersonTurnCompletedRequest(call_id="c1", text="Ada")
        )

        assert raw == b'{"call_id": "c1", "text": "Ada"}'

    def test_a_request_comes_back_equal(self) -> None:
        person_turn_completed_request_snapshot = relays.PersonTurnCompletedRequestSnapshot()
        person_turn_completed_request = relays.PersonTurnCompletedRequest(call_id="c1", text="Ada")

        returned = person_turn_completed_request_snapshot.deserialize(
            person_turn_completed_request_snapshot.serialize(person_turn_completed_request)
        )

        assert returned == person_turn_completed_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": "c1"}', b'{"call_id": "c1", "text": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonTurnCompletedRequestSnapshot().deserialize(raw)


class TestPersonTurnCompletedResponseSnapshot:
    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.PersonTurnCompletedResponseSnapshot().serialize(
            relays.PersonTurnCompletedResponse(call_id="c1")
        )

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        person_turn_completed_response_snapshot = relays.PersonTurnCompletedResponseSnapshot()
        person_turn_completed_response = relays.PersonTurnCompletedResponse(call_id="c1")

        returned = person_turn_completed_response_snapshot.deserialize(
            person_turn_completed_response_snapshot.serialize(person_turn_completed_response)
        )

        assert returned == person_turn_completed_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonTurnCompletedResponseSnapshot().deserialize(raw)
