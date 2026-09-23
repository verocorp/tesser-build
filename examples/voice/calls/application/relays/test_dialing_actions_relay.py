from __future__ import annotations

import pytest

import tesser.testing as ts

import calls.application.relays as relays
import calls.domain as domain
import tesser.errors as errors


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "Ada") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestDialPersonRequestSnapshot:

    def test_a_request_is_the_calls_snapshot(self) -> None:
        raw = relays.DialPersonRequestSnapshot().serialize(relays.DialPersonRequest(call=domain.Call(call_spec())))

        assert raw == b'{"call_id": "c1", "person_name": "Ada"}'

    def test_a_request_comes_back_carrying_the_same_call(self) -> None:
        dial_person_request_snapshot = relays.DialPersonRequestSnapshot()
        dial_person_request = relays.DialPersonRequest(call=domain.Call(call_spec(call_id="c7")))

        returned = dial_person_request_snapshot.deserialize(dial_person_request_snapshot.serialize(dial_person_request))

        assert returned.call.identity == domain.CallId("c7")
        assert returned.call.person_name == dial_person_request.call.person_name

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.DialPersonRequestSnapshot().deserialize(raw)


class TestDialPersonResponseSnapshot:

    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.DialPersonResponseSnapshot().serialize(relays.DialPersonResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        dial_person_response_snapshot = relays.DialPersonResponseSnapshot()
        dial_person_response = relays.DialPersonResponse(call_id="c1")

        returned = dial_person_response_snapshot.deserialize(dial_person_response_snapshot.serialize(dial_person_response))

        assert returned == dial_person_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.DialPersonResponseSnapshot().deserialize(raw)


class TestHangUpRequestSnapshot:

    def test_a_request_is_the_calls_snapshot(self) -> None:
        raw = relays.HangUpRequestSnapshot().serialize(relays.HangUpRequest(call=domain.Call(call_spec())))

        assert raw == b'{"call_id": "c1", "person_name": "Ada"}'

    def test_a_request_comes_back_carrying_the_same_call(self) -> None:
        hang_up_request_snapshot = relays.HangUpRequestSnapshot()
        hang_up_request = relays.HangUpRequest(call=domain.Call(call_spec(call_id="c7")))

        returned = hang_up_request_snapshot.deserialize(hang_up_request_snapshot.serialize(hang_up_request))

        assert returned.call.identity == domain.CallId("c7")
        assert returned.call.person_name == hang_up_request.call.person_name

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.HangUpRequestSnapshot().deserialize(raw)


class TestHangUpResponseSnapshot:

    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.HangUpResponseSnapshot().serialize(relays.HangUpResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        hang_up_response_snapshot = relays.HangUpResponseSnapshot()
        hang_up_response = relays.HangUpResponse(call_id="c1")

        returned = hang_up_response_snapshot.deserialize(hang_up_response_snapshot.serialize(hang_up_response))

        assert returned == hang_up_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.HangUpResponseSnapshot().deserialize(raw)
