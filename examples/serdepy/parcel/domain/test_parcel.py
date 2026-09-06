from __future__ import annotations

import ast
import pathlib
import datetime
import decimal

import pytest
import tesser.testing as ts

import parcel.domain as domain
import tesser.serialization as serialization


@ts.helper
def _spec(
    weight_kg: float = 20.5,
    items: int = 2,
    declared_value: str = "99.95",
) -> domain.ParcelSpec:
    return domain.ParcelSpec(
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
        domain.ParcelCode(value)


@pytest.mark.parametrize("value", [0, -1])
def test_item_count_rejects_a_non_positive_value(value: int) -> None:
    with pytest.raises(ValueError):
        domain.ItemCount(value)


@pytest.mark.parametrize("value", [0.0, -1.5, float("nan"), float("inf")])
def test_weight_rejects_a_non_positive_or_non_finite_value(value: float) -> None:
    with pytest.raises(ValueError):
        domain.WeightKg(value)


@pytest.mark.parametrize("value", [b"", b"short", bytes(31), bytes(33)])
def test_label_digest_rejects_a_wrong_length_value(value: bytes) -> None:
    with pytest.raises(ValueError):
        domain.LabelDigest(value)


@pytest.mark.parametrize("value", ["", "abc", "1.2.3"])
def test_declared_value_rejects_an_unparseable_value(value: str) -> None:
    with pytest.raises(ValueError):
        domain.DeclaredValue(value)


def test_declared_value_rejects_a_negative_value() -> None:
    with pytest.raises(ValueError):
        domain.DeclaredValue("-0.01")


def test_scanned_at_rejects_an_unparseable_value() -> None:
    with pytest.raises(ValueError):
        domain.ScannedAt("not-a-time")


def test_scanned_at_rejects_a_naive_timestamp() -> None:
    with pytest.raises(ValueError):
        domain.ScannedAt("2026-07-20T12:00:00")


def test_weight_class_rejects_an_unknown_value() -> None:
    with pytest.raises(ValueError, match="heavy or standard"):
        domain.WeightClass("featherweight")


def test_parcel_code_roundtrip() -> None:
    parcel_code = domain.ParcelCode("PKG-2026-0042")
    assert domain.ParcelCode(str(parcel_code)) == parcel_code


def test_item_count_roundtrip() -> None:
    item_count = domain.ItemCount(3)
    assert domain.ItemCount(int(item_count)) == item_count


def test_weight_roundtrip() -> None:
    weight_kg = domain.WeightKg(12.75)
    assert domain.WeightKg(float(weight_kg)) == weight_kg


def test_label_digest_roundtrip() -> None:
    label_digest = domain.LabelDigest(bytes(range(32)))
    assert domain.LabelDigest(bytes(label_digest)) == label_digest


def test_declared_value_roundtrip() -> None:
    declared_value = domain.DeclaredValue("199.99")
    assert domain.DeclaredValue(str(declared_value)) == declared_value


def test_scanned_at_roundtrip() -> None:
    scanned_at = domain.ScannedAt("2026-07-20T15:16:15.123456+00:00")
    assert domain.ScannedAt(str(scanned_at)) == scanned_at


def test_scanned_at_equal_instants_across_zones() -> None:
    utc = domain.ScannedAt("2026-07-20T15:16:15.123456+00:00")
    eastern = domain.ScannedAt("2026-07-20T10:16:15.123456-05:00")
    assert utc == eastern
    assert str(utc) == "2026-07-20T15:16:15.123456+00:00"
    assert str(eastern) == "2026-07-20T15:16:15.123456+00:00"


def test_decimal_policy_is_the_string_form() -> None:
    assert serialization.canonical_decimal(decimal.Decimal("199.99")) == "199.99"
    assert str(domain.DeclaredValue("1.50")) == "1.50"


def test_equal_decimals_may_have_distinct_canonical_forms() -> None:
    a, b = domain.DeclaredValue("1.5"), domain.DeclaredValue("1.50")
    assert a == b
    assert str(a) != str(b)
    assert domain.DeclaredValue(str(a)) == domain.DeclaredValue(str(b))


def test_datetime_policy_is_aware_utc_iso8601_microseconds() -> None:
    eastern = datetime.timezone(datetime.timedelta(hours=-5))
    value = datetime.datetime(2026, 7, 20, 10, 16, 15, 123456, tzinfo=eastern)
    assert serialization.canonical_datetime(value) == "2026-07-20T15:16:15.123456+00:00"
    assert serialization.canonical_datetime(datetime.datetime(2026, 7, 20, 15, 0, 0, tzinfo=datetime.timezone.utc)) == (
        "2026-07-20T15:00:00.000000+00:00"
    )


def test_datetime_policy_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        serialization.canonical_datetime(datetime.datetime(2026, 7, 20, 15, 0, 0))
    with pytest.raises(ValueError, match="timezone-aware"):
        domain.ScannedAt("2026-07-20T15:00:00")


def test_is_heavy_is_true_above_the_threshold() -> None:
    assert str(domain.Parcel(_spec(weight_kg=20.5)).weight_class()) == "heavy"


def test_is_heavy_is_false_at_and_below_the_threshold() -> None:
    assert str(domain.Parcel(_spec(weight_kg=20.0)).weight_class()) == "standard"
    assert str(domain.Parcel(_spec(weight_kg=0.5)).weight_class()) == "standard"


def test_the_compound_exposes_its_leaves_and_identity() -> None:
    parcel = domain.Parcel(_spec())
    assert parcel.code == domain.ParcelCode("ABC-123")
    assert parcel.items == domain.ItemCount(2)
    assert parcel.weight == domain.WeightKg(20.5)
    assert parcel.label_digest == domain.LabelDigest(bytes(range(32)))
    assert parcel.declared_value == domain.DeclaredValue("99.95")
    assert parcel.scanned_at == domain.ScannedAt("2026-07-20T12:00:00+00:00")
    assert parcel.identity == parcel.code


def test_the_compound_propagates_a_child_rejection() -> None:
    with pytest.raises(ValueError):
        domain.Parcel(
            domain.ParcelSpec(
                code="ABC-123",
                items=0,
                weight_kg=1.0,
                label_digest=bytes(range(32)),
                declared_value="1.00",
                scanned_at="2026-07-20T12:00:00+00:00",
            )
        )


def test_reconstruction_is_value_equal_and_non_identical() -> None:
    original = domain.Parcel(_spec())
    rebuilt = domain.Parcel(_spec())
    assert rebuilt is not original
    assert rebuilt == original


def test_reconstruction_reruns_invariants_on_stale_data() -> None:
    with pytest.raises(ValueError, match="not be negative"):
        domain.Parcel(_spec(declared_value="-1"))
    with pytest.raises(ValueError, match="item count"):
        domain.Parcel(_spec(items=0))


def test_each_leaf_defines_exactly_its_one_matching_exit() -> None:
    leaf_exits = {
        domain.ParcelCode: "__str__",
        domain.ItemCount: "__int__",
        domain.WeightKg: "__float__",
        domain.LabelDigest: "__bytes__",
        domain.DeclaredValue: "__str__",
        domain.ScannedAt: "__str__",
    }
    for cls, exit_name in leaf_exits.items():
        defined = [name for name in ("__str__", "__int__", "__float__", "__bytes__") if name in cls.__dict__]
        assert defined == [exit_name], f"{cls.__name__} defines {defined}, expected [{exit_name}]"


def test_the_entity_defines_no_conversion_dunders() -> None:
    for name in ("__str__", "__int__", "__float__", "__bytes__"):
        assert name not in domain.Parcel.__dict__, f"Parcel defines {name}"


def test_every_conversion_dunder_routes_through_a_canonical_helper() -> None:
    here = pathlib.Path(__file__).resolve().parent
    tree = ast.parse((here / "parcel.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in ("__str__", "__int__", "__float__", "__bytes__")):
            continue
        calls = {
            call.func.attr
            for call in ast.walk(node)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
        }
        assert any(name.startswith("canonical_") for name in calls), (
            f"{node.name} at parcel/domain/parcel.py line {node.lineno} does not route "
            f"through a serialization.canonical_* helper"
        )
