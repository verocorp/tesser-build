from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestAwaitPersonUtteranceRequestSnapshot:

    def test_a_request_is_its_call_id_and_the_seconds_it_waits_within(self) -> None:
        raw = relays.AwaitPersonUtteranceRequestSnapshot().serialize(
            relays.AwaitPersonUtteranceRequest(call_id="c1", within_seconds=8)
        )

        assert raw == b'{"call_id": "c1", "within_seconds": 8}'

    def test_a_request_comes_back_equal(self) -> None:
        await_person_utterance_request_snapshot = relays.AwaitPersonUtteranceRequestSnapshot()
        await_person_utterance_request = relays.AwaitPersonUtteranceRequest(call_id="c1", within_seconds=8)

        returned = await_person_utterance_request_snapshot.deserialize(
            await_person_utterance_request_snapshot.serialize(await_person_utterance_request)
        )

        assert returned == await_person_utterance_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": "c1"}', b'{"call_id": "c1", "within_seconds": "8"}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.AwaitPersonUtteranceRequestSnapshot().deserialize(raw)


class TestAwaitPersonUtteranceResponseSnapshot:

    def test_a_response_is_its_call_id_what_was_heard_and_the_text(self) -> None:
        raw = relays.AwaitPersonUtteranceResponseSnapshot().serialize(
            relays.AwaitPersonUtteranceResponse(call_id="c1", heard=relays.HEARD_UTTERANCE, text="my name is Ada")
        )

        assert raw == b'{"call_id": "c1", "heard": "utterance", "text": "my name is Ada"}'

    def test_a_response_comes_back_equal(self) -> None:
        await_person_utterance_response_snapshot = relays.AwaitPersonUtteranceResponseSnapshot()
        await_person_utterance_response = relays.AwaitPersonUtteranceResponse(
            call_id="c1", heard=relays.HEARD_SILENCE, text=""
        )

        returned = await_person_utterance_response_snapshot.deserialize(
            await_person_utterance_response_snapshot.serialize(await_person_utterance_response)
        )

        assert returned == await_person_utterance_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b"{}",
            b'{"call_id": "c1", "text": "Ada"}',
            b'{"call_id": "c1", "heard": 1, "text": "Ada"}',
            b'{"call_id": "c1", "heard": "utterance", "text": 1}',
            b'["c1"]',
        ):
            with pytest.raises(errors.DomainError):
                relays.AwaitPersonUtteranceResponseSnapshot().deserialize(raw)
