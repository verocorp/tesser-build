from __future__ import annotations

import pytest
import tesser.testing as ts

import parcel.domain.parcel as parcel

@pytest.mark.parametrize("value", ["", "lower", "BAD CODE", "A" * 33, "-LEAD"])
def test_parcel_code_rejects_a_malformed_value(value: str) -> None:
    with pytest.raises(ValueError):
        parcel.ParcelCode(value)


@pytest.mark.parametrize("value", [0, -1])
def test_item_count_rejects_a_non_positive_value(value: int) -> None:
    with pytest.raises(ValueError):
        parcel.ItemCount(value)


@pytest.mark.parametrize("value", [0.0, -1.5, float("nan"), float("inf")])
def test_weight_rejects_a_non_positive_or_non_finite_value(value: float) -> None:
    with pytest.raises(ValueError):
        parcel.WeightKg(value)


@pytest.mark.parametrize("value", [b"", b"short", bytes(31), bytes(33)])
def test_label_digest_rejects_a_wrong_length_value(value: bytes) -> None:
    with pytest.raises(ValueError):
        parcel.LabelDigest(value)


@pytest.mark.parametrize("value", ["", "abc", "1.2.3"])
def test_declared_value_rejects_an_unparseable_value(value: str) -> None:
    with pytest.raises(ValueError):
        parcel.DeclaredValue(value)


def test_declared_value_rejects_a_negative_value() -> None:
    with pytest.raises(ValueError):
        parcel.DeclaredValue("-0.01")


def test_scanned_at_rejects_an_unparseable_value() -> None:
    with pytest.raises(ValueError):
        parcel.ScannedAt("not-a-time")


def test_scanned_at_rejects_a_naive_timestamp() -> None:
    with pytest.raises(ValueError):
        parcel.ScannedAt("2026-07-20T12:00:00")


@ts.helper
def _spec(weight_kg: float = 20.5) -> parcel.ParcelSpec:
    return parcel.ParcelSpec(
        code="ABC-123",
        items=2,
        weight_kg=weight_kg,
        label_digest=bytes(range(32)),
        declared_value="99.95",
        scanned_at="2026-07-20T12:00:00+00:00",
    )


def test_is_heavy_is_true_above_the_threshold() -> None:
    assert str(parcel.Parcel(_spec(20.5)).weight_class()) == "heavy"


def test_is_heavy_is_false_at_and_below_the_threshold() -> None:
    assert str(parcel.Parcel(_spec(20.0)).weight_class()) == "standard"
    assert str(parcel.Parcel(_spec(0.5)).weight_class()) == "standard"


def test_the_compound_propagates_a_child_rejection() -> None:
    with pytest.raises(ValueError):
        parcel.Parcel(
            parcel.ParcelSpec(
                code="ABC-123",
                items=0,
                weight_kg=1.0,
                label_digest=bytes(range(32)),
                declared_value="1.00",
                scanned_at="2026-07-20T12:00:00+00:00",
            )
        )
