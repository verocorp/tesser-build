from __future__ import annotations

import pytest
import tesser.testing as ts

import parcel.application.parts as parts
import parcel.domain.parcel as parcel


@ts.helper
def _spec(items: int = 3, declared_value: str = "199.99") -> parcel.ParcelSpec:
    return parcel.ParcelSpec(
        code="PKG-2026-0042",
        items=items,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value=declared_value,
        scanned_at="2026-07-20T10:16:15.123456-05:00",
    )


def test_reconstruction_is_value_equal_and_non_identical() -> None:
    original = parcel.Parcel(_spec())
    rebuilt = parcel.Parcel(_spec())
    assert rebuilt is not original
    assert rebuilt == original


def test_reconstruction_reruns_invariants_on_stale_data() -> None:
    with pytest.raises(ValueError, match="not be negative"):
        parcel.Parcel(_spec(declared_value="-1"))
    with pytest.raises(ValueError, match="item count"):
        parcel.Parcel(_spec(items=0))


def test_parts_from_equal_parcels_render_identically() -> None:
    a = parts.parcel_parts(parcel.Parcel(_spec()))
    b = parts.parcel_parts(parcel.Parcel(_spec()))
    assert (a.code, a.items, a.weight_kg, a.heavy) == (b.code, b.items, b.weight_kg, b.heavy)
