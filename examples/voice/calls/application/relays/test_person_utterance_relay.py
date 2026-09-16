from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestPersonUtteranceRequestSnapshot:

    def test_a_request_is_its_call_id_and_text(self) -> None:
        raw = relays.PersonUtteranceRequestSnapshot().serialize(
            relays.PersonUtteranceRequest(call_id="c1", text="my name is Ada")
        )

        assert raw == b'{"call_id": "c1", "text": "my name is Ada"}'

    def test_a_request_comes_back_equal(self) -> None:
        person_utterance_request_snapshot = relays.PersonUtteranceRequestSnapshot()
        person_utterance_request = relays.PersonUtteranceRequest(call_id="c1", text="my name is Ada")

        returned = person_utterance_request_snapshot.deserialize(
            person_utterance_request_snapshot.serialize(person_utterance_request)
        )

        assert returned == person_utterance_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": "c1"}', b'{"call_id": "c1", "text": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonUtteranceRequestSnapshot().deserialize(raw)


class TestPersonUtteranceResponseSnapshot:

    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.PersonUtteranceResponseSnapshot().serialize(relays.PersonUtteranceResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        person_utterance_response_snapshot = relays.PersonUtteranceResponseSnapshot()
        person_utterance_response = relays.PersonUtteranceResponse(call_id="c1")

        returned = person_utterance_response_snapshot.deserialize(
            person_utterance_response_snapshot.serialize(person_utterance_response)
        )

        assert returned == person_utterance_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.PersonUtteranceResponseSnapshot().deserialize(raw)
