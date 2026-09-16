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
