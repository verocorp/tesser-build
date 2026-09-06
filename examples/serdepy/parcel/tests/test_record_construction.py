from __future__ import annotations

import inspect

import tesser.testing as ts

import parcel.application.ports as ports
import parcel.domain as domain

@ts.helper
def _spec(items: int = 3, declared_value: str = "199.99") -> domain.ParcelSpec:
    return domain.ParcelSpec(
        code="PKG-2026-0042",
        items=items,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value=declared_value,
        scanned_at="2026-07-20T10:16:15.123456-05:00",
    )


def test_mapping_carries_typed_canonical_leaves_and_derived_fields() -> None:
    parcel = domain.Parcel(_spec())
    parcel_record = ports.ParcelRecord(
        code=str(parcel.code),
        items=int(parcel.items),
        weight_kg=float(parcel.weight),
        label_digest=bytes(parcel.label_digest),
        declared_value=str(parcel.declared_value),
        scanned_at=str(parcel.scanned_at),
        weight_class=(
            ports.WeightClass.HEAVY
            if str(parcel.weight_class()) == "heavy"
            else ports.WeightClass.LIGHT
        ),
    )
    assert parcel_record.code == "PKG-2026-0042"
    assert parcel_record.items == 3
    assert parcel_record.weight_kg == 21.5
    assert parcel_record.label_digest == bytes(range(32))
    assert parcel_record.declared_value == "199.99"
    assert parcel_record.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert parcel_record.weight_class is ports.WeightClass.HEAVY


def test_records_from_equal_parcels_render_identically() -> None:
    parcel = domain.Parcel(_spec())
    a = ports.ParcelRecord(
        code=str(parcel.code),
        items=int(parcel.items),
        weight_kg=float(parcel.weight),
        label_digest=bytes(parcel.label_digest),
        declared_value=str(parcel.declared_value),
        scanned_at=str(parcel.scanned_at),
        weight_class=(
            ports.WeightClass.HEAVY
            if str(parcel.weight_class()) == "heavy"
            else ports.WeightClass.LIGHT
        ),
    )
    parcel = domain.Parcel(_spec())
    b = ports.ParcelRecord(
        code=str(parcel.code),
        items=int(parcel.items),
        weight_kg=float(parcel.weight),
        label_digest=bytes(parcel.label_digest),
        declared_value=str(parcel.declared_value),
        scanned_at=str(parcel.scanned_at),
        weight_class=(
            ports.WeightClass.HEAVY
            if str(parcel.weight_class()) == "heavy"
            else ports.WeightClass.LIGHT
        ),
    )
    assert (a.code, a.items, a.weight_kg, a.weight_class) == (b.code, b.items, b.weight_kg, b.weight_class)
    assert (a.label_digest, a.declared_value, a.scanned_at) == (
        b.label_digest,
        b.declared_value,
        b.scanned_at,
    )


def test_record_carries_a_changed_leaf_through_the_mapping() -> None:
    parcel = domain.Parcel(_spec(items=7, declared_value="0.01"))
    parcel_record = ports.ParcelRecord(
        code=str(parcel.code),
        items=int(parcel.items),
        weight_kg=float(parcel.weight),
        label_digest=bytes(parcel.label_digest),
        declared_value=str(parcel.declared_value),
        scanned_at=str(parcel.scanned_at),
        weight_class=(
            ports.WeightClass.HEAVY
            if str(parcel.weight_class()) == "heavy"
            else ports.WeightClass.LIGHT
        ),
    )
    assert parcel_record.items == 7
    assert parcel_record.declared_value == "0.01"


def test_record_diverges_from_spec_by_construction() -> None:
    record_fields = {n for n in inspect.signature(ports.ParcelRecord.__init__).parameters if n != "self"}
    spec_fields = {n for n in inspect.signature(domain.ParcelSpec.__init__).parameters if n != "self"}
    derived = record_fields - spec_fields
    assert derived == {"weight_class"}, "the parcel_record must carry derived fields the constructor never accepts"
    assert "weight_class" not in spec_fields


def test_record_is_total() -> None:
    for name, param in inspect.signature(ports.ParcelRecord.__init__).parameters.items():
        if name == "self":
            continue
        assert param.default is inspect.Parameter.empty, f"{name} must have no default"
