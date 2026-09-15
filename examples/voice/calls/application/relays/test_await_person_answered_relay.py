from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestAwaitPersonAnsweredRequestSnapshot:

    def test_a_request_is_its_call_id(self) -> None:
        raw = relays.AwaitPersonAnsweredRequestSnapshot().serialize(relays.AwaitPersonAnsweredRequest(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_request_comes_back_equal(self) -> None:
        await_person_answered_request_snapshot = relays.AwaitPersonAnsweredRequestSnapshot()
        await_person_answered_request = relays.AwaitPersonAnsweredRequest(call_id="c1")

        returned = await_person_answered_request_snapshot.deserialize(
            await_person_answered_request_snapshot.serialize(await_person_answered_request)
        )

        assert returned == await_person_answered_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.AwaitPersonAnsweredRequestSnapshot().deserialize(raw)


class TestAwaitPersonAnsweredResponseSnapshot:

    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.AwaitPersonAnsweredResponseSnapshot().serialize(
            relays.AwaitPersonAnsweredResponse(call_id="c1")
        )

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        await_person_answered_response_snapshot = relays.AwaitPersonAnsweredResponseSnapshot()
        await_person_answered_response = relays.AwaitPersonAnsweredResponse(call_id="c1")

        returned = await_person_answered_response_snapshot.deserialize(
            await_person_answered_response_snapshot.serialize(await_person_answered_response)
        )

        assert returned == await_person_answered_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.AwaitPersonAnsweredResponseSnapshot().deserialize(raw)
