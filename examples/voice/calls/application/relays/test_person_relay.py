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
        raw = relays.AwaitPersonAnsweredResponseSnapshot().serialize(relays.AwaitPersonAnsweredResponse(call_id="c1"))

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


class TestAwaitPersonInputRequestSnapshot:
    def test_a_request_is_its_call_id_and_the_seconds_it_waits_within(self) -> None:
        raw = relays.AwaitPersonInputRequestSnapshot().serialize(
            relays.AwaitPersonInputRequest(call_id="c1", within_seconds=8)
        )

        assert raw == b'{"call_id": "c1", "within_seconds": 8}'

    def test_a_request_comes_back_equal(self) -> None:
        await_person_input_request_snapshot = relays.AwaitPersonInputRequestSnapshot()
        await_person_input_request = relays.AwaitPersonInputRequest(call_id="c1", within_seconds=8)

        returned = await_person_input_request_snapshot.deserialize(
            await_person_input_request_snapshot.serialize(await_person_input_request)
        )

        assert returned == await_person_input_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": "c1"}', b'{"call_id": "c1", "within_seconds": "8"}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.AwaitPersonInputRequestSnapshot().deserialize(raw)


class TestAwaitPersonInputResponseSnapshot:
    def test_a_response_is_its_call_id_what_was_heard_and_the_text(self) -> None:
        raw = relays.AwaitPersonInputResponseSnapshot().serialize(
            relays.AwaitPersonInputResponse(call_id="c1", kind=relays.INPUT_TURN_COMPLETED, text="my name is Ada")
        )

        assert raw == b'{"call_id": "c1", "kind": "turn_completed", "text": "my name is Ada"}'

    def test_a_response_comes_back_equal(self) -> None:
        await_person_input_response_snapshot = relays.AwaitPersonInputResponseSnapshot()
        await_person_input_response = relays.AwaitPersonInputResponse(
            call_id="c1", kind=relays.INPUT_NO_RESPONSE, text=""
        )

        returned = await_person_input_response_snapshot.deserialize(
            await_person_input_response_snapshot.serialize(await_person_input_response)
        )

        assert returned == await_person_input_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b"{}",
            b'{"call_id": "c1", "text": "Ada"}',
            b'{"call_id": "c1", "kind": 1, "text": "Ada"}',
            b'{"call_id": "c1", "kind": "turn_completed", "text": 1}',
            b'["c1"]',
        ):
            with pytest.raises(errors.DomainError):
                relays.AwaitPersonInputResponseSnapshot().deserialize(raw)
