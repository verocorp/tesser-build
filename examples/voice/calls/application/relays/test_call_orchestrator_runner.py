from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestPlaceCallRequestSnapshot:

    def test_a_request_is_its_call_id_person_name_and_phone_number(self) -> None:
        place_call_request = relays.PlaceCallRequest(call_id="c1", person_name="Ada", phone_number="+15555550100")

        raw = relays.PlaceCallRequestSnapshot().serialize(place_call_request)

        assert raw == b'{"call_id": "c1", "person_name": "Ada", "phone_number": "+15555550100"}'

    def test_a_request_comes_back_equal(self) -> None:
        place_call_request_snapshot = relays.PlaceCallRequestSnapshot()
        place_call_request = relays.PlaceCallRequest(call_id="c1", person_name="Ada", phone_number="+15555550100")

        returned = place_call_request_snapshot.deserialize(place_call_request_snapshot.serialize(place_call_request))

        assert returned == place_call_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1, "person_name": "Ada", "phone_number": "p"}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PlaceCallRequestSnapshot().deserialize(raw)


class TestPlaceCallResponseSnapshot:

    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.PlaceCallResponseSnapshot().serialize(relays.PlaceCallResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        place_call_response_snapshot = relays.PlaceCallResponseSnapshot()
        place_call_response = relays.PlaceCallResponse(call_id="c1")

        returned = place_call_response_snapshot.deserialize(place_call_response_snapshot.serialize(place_call_response))

        assert returned == place_call_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PlaceCallResponseSnapshot().deserialize(raw)
