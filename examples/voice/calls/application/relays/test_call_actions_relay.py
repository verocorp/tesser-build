from __future__ import annotations

import pytest

import tesser.testing as ts

import calls.application.relays as relays
import calls.domain as domain
import tesser.errors as errors


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "Ada") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestRecordCallRequestSnapshot:

    def test_a_request_is_the_calls_snapshot(self) -> None:
        raw = relays.RecordCallRequestSnapshot().serialize(relays.RecordCallRequest(call=domain.Call(call_spec())))

        assert raw == b'{"call_id": "c1", "person_name": "Ada"}'

    def test_a_request_comes_back_carrying_the_same_call(self) -> None:
        record_call_request_snapshot = relays.RecordCallRequestSnapshot()
        record_call_request = relays.RecordCallRequest(call=domain.Call(call_spec(call_id="c7", person_name="Grace")))

        returned = record_call_request_snapshot.deserialize(record_call_request_snapshot.serialize(record_call_request))

        assert returned.call.identity == domain.CallId("c7")
        assert returned.call.person_name == record_call_request.call.person_name

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
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
