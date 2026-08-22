from __future__ import annotations

import inspect

import tesser.testing as ts

import parcel.application.ports.parcel_wire as parcel_wire
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


def test_mapping_carries_typed_canonical_leaves_and_derived_fields() -> None:
    built = parcel.Parcel(_spec())
    record = parcel_wire.ParcelRecord(
        code=str(built.code),
        items=int(built.items),
        weight_kg=float(built.weight),
        label_digest=bytes(built.label_digest),
        declared_value=str(built.declared_value),
        scanned_at=str(built.scanned_at),
        weight_class=(
            parcel_wire.WeightClass.HEAVY
            if str(built.weight_class()) == "heavy"
            else parcel_wire.WeightClass.LIGHT
        ),
    )
    assert record.code == "PKG-2026-0042"
    assert record.items == 3
    assert record.weight_kg == 21.5
    assert record.label_digest == bytes(range(32))
    assert record.declared_value == "199.99"
    assert record.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert record.weight_class is parcel_wire.WeightClass.HEAVY


def test_records_from_equal_parcels_render_identically() -> None:
    built = parcel.Parcel(_spec())
    a = parcel_wire.ParcelRecord(
        code=str(built.code),
        items=int(built.items),
        weight_kg=float(built.weight),
        label_digest=bytes(built.label_digest),
        declared_value=str(built.declared_value),
        scanned_at=str(built.scanned_at),
        weight_class=(
            parcel_wire.WeightClass.HEAVY
            if str(built.weight_class()) == "heavy"
            else parcel_wire.WeightClass.LIGHT
        ),
    )
    built = parcel.Parcel(_spec())
    b = parcel_wire.ParcelRecord(
        code=str(built.code),
        items=int(built.items),
        weight_kg=float(built.weight),
        label_digest=bytes(built.label_digest),
        declared_value=str(built.declared_value),
        scanned_at=str(built.scanned_at),
        weight_class=(
            parcel_wire.WeightClass.HEAVY
            if str(built.weight_class()) == "heavy"
            else parcel_wire.WeightClass.LIGHT
        ),
    )
    assert (a.code, a.items, a.weight_kg, a.weight_class) == (b.code, b.items, b.weight_kg, b.weight_class)
    assert (a.label_digest, a.declared_value, a.scanned_at) == (
        b.label_digest,
        b.declared_value,
        b.scanned_at,
    )


def test_record_carries_a_changed_leaf_through_the_mapping() -> None:
    built = parcel.Parcel(_spec(items=7, declared_value="0.01"))
    record = parcel_wire.ParcelRecord(
        code=str(built.code),
        items=int(built.items),
        weight_kg=float(built.weight),
        label_digest=bytes(built.label_digest),
        declared_value=str(built.declared_value),
        scanned_at=str(built.scanned_at),
        weight_class=(
            parcel_wire.WeightClass.HEAVY
            if str(built.weight_class()) == "heavy"
            else parcel_wire.WeightClass.LIGHT
        ),
    )
    assert record.items == 7
    assert record.declared_value == "0.01"


def test_record_diverges_from_spec_by_construction() -> None:
    record_fields = {n for n in inspect.signature(parcel_wire.ParcelRecord.__init__).parameters if n != "self"}
    spec_fields = {n for n in inspect.signature(parcel.ParcelSpec.__init__).parameters if n != "self"}
    derived = record_fields - spec_fields
    assert derived == {"weight_class"}, "the record must carry derived fields the constructor never accepts"
    assert "weight_class" not in spec_fields


def test_record_is_total() -> None:
    for name, param in inspect.signature(parcel_wire.ParcelRecord.__init__).parameters.items():
        if name == "self":
            continue
        assert param.default is inspect.Parameter.empty, f"{name} must have no default"
