from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestRecordCallRequestSnapshot:

    def test_a_request_is_its_call_id_person_name_and_phone_number(self) -> None:
        record_call_request = relays.RecordCallRequest(call_id="c1", person_name="Ada", phone_number="+15555550100")

        raw = relays.RecordCallRequestSnapshot().serialize(record_call_request)

        assert raw == b'{"call_id": "c1", "person_name": "Ada", "phone_number": "+15555550100"}'

    def test_a_request_comes_back_equal(self) -> None:
        record_call_request_snapshot = relays.RecordCallRequestSnapshot()
        record_call_request = relays.RecordCallRequest(call_id="c1", person_name="Ada", phone_number="+15555550100")

        returned = record_call_request_snapshot.deserialize(record_call_request_snapshot.serialize(record_call_request))

        assert returned == record_call_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1, "person_name": "Ada", "phone_number": "p"}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.RecordCallRequestSnapshot().deserialize(raw)


class TestRecordCallResponseSnapshot:

    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.RecordCallResponseSnapshot().serialize(relays.RecordCallResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        record_call_response_snapshot = relays.RecordCallResponseSnapshot()
        record_call_response = relays.RecordCallResponse(call_id="c1")

        returned = record_call_response_snapshot.deserialize(record_call_response_snapshot.serialize(record_call_response))

        assert returned == record_call_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.RecordCallResponseSnapshot().deserialize(raw)
