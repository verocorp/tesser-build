from __future__ import annotations

import ast
import pathlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import tesser.testing as ts

import parcel.domain.parcel as parcel
from tesser.serialization import canonical_datetime, canonical_decimal


@ts.helper
def _spec(
    weight_kg: float = 20.5,
    items: int = 2,
    declared_value: str = "99.95",
) -> parcel.ParcelSpec:
    return parcel.ParcelSpec(
        code="ABC-123",
        items=items,
        weight_kg=weight_kg,
        label_digest=bytes(range(32)),
        declared_value=declared_value,
        scanned_at="2026-07-20T12:00:00+00:00",
    )


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


def test_weight_class_rejects_an_unknown_value() -> None:
    with pytest.raises(ValueError, match="heavy or standard"):
        parcel.WeightClass("featherweight")


def test_parcel_code_roundtrip() -> None:
    code = parcel.ParcelCode("PKG-2026-0042")
    assert parcel.ParcelCode(str(code)) == code


def test_item_count_roundtrip() -> None:
    count = parcel.ItemCount(3)
    assert parcel.ItemCount(int(count)) == count


def test_weight_roundtrip() -> None:
    weight = parcel.WeightKg(12.75)
    assert parcel.WeightKg(float(weight)) == weight


def test_label_digest_roundtrip() -> None:
    digest = parcel.LabelDigest(bytes(range(32)))
    assert parcel.LabelDigest(bytes(digest)) == digest


def test_declared_value_roundtrip() -> None:
    value = parcel.DeclaredValue("199.99")
    assert parcel.DeclaredValue(str(value)) == value


def test_scanned_at_roundtrip() -> None:
    scanned = parcel.ScannedAt("2026-07-20T15:16:15.123456+00:00")
    assert parcel.ScannedAt(str(scanned)) == scanned


def test_scanned_at_equal_instants_across_zones() -> None:
    utc = parcel.ScannedAt("2026-07-20T15:16:15.123456+00:00")
    eastern = parcel.ScannedAt("2026-07-20T10:16:15.123456-05:00")
    assert utc == eastern
    assert str(utc) == "2026-07-20T15:16:15.123456+00:00"
    assert str(eastern) == "2026-07-20T15:16:15.123456+00:00"


def test_decimal_policy_is_the_string_form() -> None:
    assert canonical_decimal(Decimal("199.99")) == "199.99"
    assert str(parcel.DeclaredValue("1.50")) == "1.50"


def test_equal_decimals_may_have_distinct_canonical_forms() -> None:
    a, b = parcel.DeclaredValue("1.5"), parcel.DeclaredValue("1.50")
    assert a == b
    assert str(a) != str(b)
    assert parcel.DeclaredValue(str(a)) == parcel.DeclaredValue(str(b))


def test_datetime_policy_is_aware_utc_iso8601_microseconds() -> None:
    eastern = timezone(timedelta(hours=-5))
    value = datetime(2026, 7, 20, 10, 16, 15, 123456, tzinfo=eastern)
    assert canonical_datetime(value) == "2026-07-20T15:16:15.123456+00:00"
    assert canonical_datetime(datetime(2026, 7, 20, 15, 0, 0, tzinfo=timezone.utc)) == (
        "2026-07-20T15:00:00.000000+00:00"
    )


def test_datetime_policy_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        canonical_datetime(datetime(2026, 7, 20, 15, 0, 0))
    with pytest.raises(ValueError, match="timezone-aware"):
        parcel.ScannedAt("2026-07-20T15:00:00")


def test_is_heavy_is_true_above_the_threshold() -> None:
    assert str(parcel.Parcel(_spec(weight_kg=20.5)).weight_class()) == "heavy"


def test_is_heavy_is_false_at_and_below_the_threshold() -> None:
    assert str(parcel.Parcel(_spec(weight_kg=20.0)).weight_class()) == "standard"
    assert str(parcel.Parcel(_spec(weight_kg=0.5)).weight_class()) == "standard"


def test_the_compound_exposes_its_leaves_and_identity() -> None:
    built = parcel.Parcel(_spec())
    assert built.code == parcel.ParcelCode("ABC-123")
    assert built.items == parcel.ItemCount(2)
    assert built.weight == parcel.WeightKg(20.5)
    assert built.label_digest == parcel.LabelDigest(bytes(range(32)))
    assert built.declared_value == parcel.DeclaredValue("99.95")
    assert built.scanned_at == parcel.ScannedAt("2026-07-20T12:00:00+00:00")
    assert built.identity == built.code


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


def test_each_leaf_defines_exactly_its_one_matching_exit() -> None:
    leaf_exits = {
        parcel.ParcelCode: "__str__",
        parcel.ItemCount: "__int__",
        parcel.WeightKg: "__float__",
        parcel.LabelDigest: "__bytes__",
        parcel.DeclaredValue: "__str__",
        parcel.ScannedAt: "__str__",
    }
    for cls, exit_name in leaf_exits.items():
        defined = [name for name in ("__str__", "__int__", "__float__", "__bytes__") if name in cls.__dict__]
        assert defined == [exit_name], f"{cls.__name__} defines {defined}, expected [{exit_name}]"


def test_the_entity_defines_no_conversion_dunders() -> None:
    for name in ("__str__", "__int__", "__float__", "__bytes__"):
        assert name not in parcel.Parcel.__dict__, f"Parcel defines {name}"


def test_every_conversion_dunder_routes_through_a_canonical_helper() -> None:
    here = pathlib.Path(__file__).resolve().parent
    tree = ast.parse((here / "parcel.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in ("__str__", "__int__", "__float__", "__bytes__")):
            continue
        calls = {
            call.func.id
            for call in ast.walk(node)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        }
        assert any(name.startswith("canonical_") for name in calls), (
            f"{node.name} at parcel/domain/parcel.py line {node.lineno} does not route "
            f"through a serialization.canonical_* helper"
        )
