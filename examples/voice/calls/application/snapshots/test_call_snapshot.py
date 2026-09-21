from __future__ import annotations

import pytest

import tesser.testing as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "Ada") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestCallSnapshot:

    def test_the_snapshot_is_the_calls_canonical_form(self) -> None:
        call = domain.Call(call_spec())

        raw = snapshots.CallSnapshot().serialize(call)

        assert raw == b'{"call_id": "c1", "person_name": "Ada"}'

    def test_a_call_comes_back_whole_through_its_own_constructor(self) -> None:
        call_snapshot = snapshots.CallSnapshot()
        call = domain.Call(call_spec(call_id="c7", person_name="Grace"))

        back = call_snapshot.deserialize(call_snapshot.serialize(call))

        assert back.identity == domain.CallId("c7")
        assert back.person_name == call.person_name

    def test_a_snapshot_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b"{}",
            b'{"call_id": "c1"}',
            b'{"person_name": "Ada"}',
            b'{"call_id": 1, "person_name": "Ada"}',
            b'{"call_id": "c1", "person_name": 1}',
            b'["c1"]',
        ):
            with pytest.raises(errors.DomainError):
                snapshots.CallSnapshot().deserialize(raw)
