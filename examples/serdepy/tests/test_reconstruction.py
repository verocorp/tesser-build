from __future__ import annotations

import dataclasses

import pytest

from parcel import Parcel, ParcelSpec
from parts import parcel_parts


def _spec() -> ParcelSpec:
    return ParcelSpec(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value="199.99",
        scanned_at="2026-07-20T10:16:15.123456-05:00",
    )


def test_reconstruction_is_value_equal_and_non_identical() -> None:
    original = Parcel(_spec())
    rebuilt = Parcel(_spec())
    assert rebuilt is not original
    assert parcel_parts(rebuilt) == parcel_parts(original)


def test_reconstruction_reruns_invariants_on_stale_data() -> None:
    with pytest.raises(ValueError, match="not be negative"):
        Parcel(dataclasses.replace(_spec(), declared_value="-1"))
    with pytest.raises(ValueError, match="item count"):
        Parcel(dataclasses.replace(_spec(), items=0))
