from __future__ import annotations

import ast
import inspect
import pathlib

import tesser.testing as ts

import parcel.application.parts as parts
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


def test_parts_carries_typed_canonical_leaves_and_derived_fields() -> None:
    record = parts.parcel_parts(parcel.Parcel(_spec()))
    assert record.code == "PKG-2026-0042"
    assert record.items == 3
    assert record.weight_kg == 21.5
    assert record.label_digest == bytes(range(32))
    assert record.declared_value == "199.99"
    assert record.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert record.heavy is True


def test_parts_diverges_from_spec_by_construction() -> None:
    parts_fields = {n for n in inspect.signature(parts.ParcelParts.__init__).parameters if n != "self"}
    spec_fields = {n for n in inspect.signature(parcel.ParcelSpec.__init__).parameters if n != "self"}
    derived = parts_fields - spec_fields
    assert derived == {"heavy"}, "parts must carry derived fields the constructor never accepts"
    assert "heavy" not in spec_fields


def test_parts_record_is_total() -> None:
    for name, param in inspect.signature(parts.ParcelParts.__init__).parameters.items():
        if name == "self":
            continue
        assert param.default is inspect.Parameter.empty, f"{name} must have no default"


def test_parts_module_never_touches_specs() -> None:
    here = pathlib.Path(__file__).resolve().parent
    source = (here / "parts.py").read_text(encoding="utf-8")
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
    assert not spec_touches, f"parts is outbound-only; it must never touch specs: {spec_touches}"
