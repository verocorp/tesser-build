from __future__ import annotations

import pytest

import calls.application.relays as relays
import tesser.errors as errors


class TestAwaitPersonJoinedResponseSnapshot:
    def test_a_response_is_its_call_id(self) -> None:
        raw = relays.AwaitPersonJoinedResponseSnapshot().serialize(relays.AwaitPersonJoinedResponse(call_id="c1"))

        assert raw == b'{"call_id": "c1"}'

    def test_a_response_comes_back_equal(self) -> None:
        await_person_joined_response_snapshot = relays.AwaitPersonJoinedResponseSnapshot()
        await_person_joined_response = relays.AwaitPersonJoinedResponse(call_id="c1")

        returned = await_person_joined_response_snapshot.deserialize(
            await_person_joined_response_snapshot.serialize(await_person_joined_response)
        )

        assert returned == await_person_joined_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.AwaitPersonJoinedResponseSnapshot().deserialize(raw)


class TestAwaitPersonTurnResponseSnapshot:
    def test_a_response_is_its_call_id_and_the_text_the_person_said(self) -> None:
        raw = relays.AwaitPersonTurnResponseSnapshot().serialize(
            relays.AwaitPersonTurnResponse(call_id="c1", text="Ada")
        )

        assert raw == b'{"call_id": "c1", "text": "Ada"}'

    def test_a_response_comes_back_equal(self) -> None:
        await_person_turn_response_snapshot = relays.AwaitPersonTurnResponseSnapshot()
        await_person_turn_response = relays.AwaitPersonTurnResponse(call_id="c1", text="Ada")

        returned = await_person_turn_response_snapshot.deserialize(
            await_person_turn_response_snapshot.serialize(await_person_turn_response)
        )

        assert returned == await_person_turn_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b"{}", b'{"call_id": "c1"}', b'{"call_id": "c1", "text": 1}', b'["c1"]'):
            with pytest.raises(errors.DomainError):
                relays.AwaitPersonTurnResponseSnapshot().deserialize(raw)
