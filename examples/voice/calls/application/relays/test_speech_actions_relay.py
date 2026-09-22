from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestSayUtteranceRequestSnapshot:
    def test_a_request_is_its_call_id_and_the_text_to_say(self) -> None:
        raw = relays.SayUtteranceRequestSnapshot().serialize(
            relays.SayUtteranceRequest(call_id="c1", text="Nice to meet you, Ada. Goodbye.")
        )

        assert raw == b'{"call_id": "c1", "text": "Nice to meet you, Ada. Goodbye."}'

    def test_a_request_comes_back_equal(self) -> None:
        say_utterance_request_snapshot = relays.SayUtteranceRequestSnapshot()
        say_utterance_request = relays.SayUtteranceRequest(call_id="c1", text="Nice to meet you, Ada. Goodbye.")

        returned = say_utterance_request_snapshot.deserialize(
            say_utterance_request_snapshot.serialize(say_utterance_request)
        )

        assert returned == say_utterance_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": "c1"}', b'{"call_id": "c1", "text": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.SayUtteranceRequestSnapshot().deserialize(raw)


class TestSayUtteranceResponseSnapshot:
    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.SayUtteranceResponseSnapshot().serialize(relays.SayUtteranceResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        say_utterance_response_snapshot = relays.SayUtteranceResponseSnapshot()
        say_utterance_response = relays.SayUtteranceResponse(call_id="c1")

        returned = say_utterance_response_snapshot.deserialize(
            say_utterance_response_snapshot.serialize(say_utterance_response)
        )

        assert returned == say_utterance_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.SayUtteranceResponseSnapshot().deserialize(raw)
