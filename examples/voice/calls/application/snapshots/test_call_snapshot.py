from __future__ import annotations

import pytest

import tesser.testing as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


@ts.helper
def call_spec(
    call_id: str = "c1", name: str = "Ada", phone_number: str = "+15555550100", step: str = "ask_name"
) -> domain.CallSpec:
    return domain.CallSpec(
        call_id=call_id,
        person=domain.PersonSpec(name=name, phone_number=phone_number),
        turns=(domain.TurnSpec(speaker="agent", utterances=("hi, may I have your name?",)),),
        step=step,
    )


class TestCallSnapshot:

    def test_the_snapshot_is_the_calls_canonical_form(self) -> None:
        call = domain.Call(call_spec())

        raw = snapshots.CallSnapshot().serialize(call)

        assert raw == (
            b'{"call_id": "c1", "person": {"name": "Ada", "phone_number": "+15555550100"}, '
            b'"turns": [{"speaker": "agent", "utterances": ["hi, may I have your name?"]}], "step": "ask_name"}'
        )

    def test_a_call_comes_back_whole_through_its_own_constructor(self) -> None:
        call_snapshot = snapshots.CallSnapshot()
        call = domain.Call(call_spec(call_id="c7", name="Grace", step="done"))

        back = call_snapshot.deserialize(call_snapshot.serialize(call))

        assert back.identity == domain.CallId("c7")
        assert back.person == call.person
        assert back.conversation == call.conversation
        assert back.step == domain.CallStep("done")

    def test_a_snapshot_that_breaks_an_invariant_is_refused_on_the_way_in(self) -> None:
        with pytest.raises(errors.DomainError):
            snapshots.CallSnapshot().deserialize(
                b'{"call_id": "c1", "person": {"name": "Ada", "phone_number": "p"}, "turns": [], "step": "haggle"}'
            )

    def test_a_snapshot_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b"{}",
            b'{"call_id": "c1", "person": "Ada", "turns": [], "step": "ask_name"}',
            b'{"call_id": "c1", "person": {"name": "Ada", "phone_number": "p"}, "turns": [1], "step": "ask_name"}',
            b'{"call_id": "c1", "person": {"name": "Ada", "phone_number": "p"}, '
            b'"turns": [{"speaker": "agent", "utterances": [1]}], "step": "ask_name"}',
            b'{"call_id": "c1", "person": {"name": "Ada", "phone_number": "p"}, "turns": [], "step": 1}',
        ):
            with pytest.raises(errors.DomainError):
                snapshots.CallSnapshot().deserialize(raw)
