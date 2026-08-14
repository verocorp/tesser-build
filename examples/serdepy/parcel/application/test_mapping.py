from __future__ import annotations

import ast
import inspect
import pathlib

import tesser.testing as ts

import parcel.application.mapping as mapping
import parcel.application.ports.parcel_wire as parcel_wire
import parcel.domain.parcel as parcel

@ts.helper
def _spec() -> parcel.ParcelSpec:
    return parcel.ParcelSpec(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value="199.99",
        scanned_at="2026-07-20T10:16:15.123456-05:00",
    )


def test_mapping_carries_typed_canonical_leaves_and_derived_fields() -> None:
    record = mapping.parcel_record(parcel.Parcel(_spec()))
    assert record.code == "PKG-2026-0042"
    assert record.items == 3
    assert record.weight_kg == 21.5
    assert record.label_digest == bytes(range(32))
    assert record.declared_value == "199.99"
    assert record.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert record.weight_class is parcel_wire.WeightClass.HEAVY


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


def test_mapping_module_never_touches_specs() -> None:
    here = pathlib.Path(__file__).resolve().parent
    source = (here / "mapping.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    spec_touches = {
        name for name in imported | referenced | attributes if name.endswith("Spec")
    }
    assert not spec_touches, f"mapping is outbound-only; it must never touch specs: {spec_touches}"
