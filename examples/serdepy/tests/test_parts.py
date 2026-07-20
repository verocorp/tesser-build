from __future__ import annotations

import ast
import dataclasses
import pathlib

from parcel import Parcel, ParcelSpec
from parts import ParcelParts, parcel_parts

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _spec() -> ParcelSpec:
    return ParcelSpec(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value="199.99",
        scanned_at="2026-07-20T10:16:15.123456-05:00",
    )


def test_parts_carries_typed_canonical_leaves_and_derived_fields() -> None:
    parts = parcel_parts(Parcel(_spec()))
    assert parts == ParcelParts(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value="199.99",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        heavy=True,
    )


def test_parts_diverges_from_spec_by_construction() -> None:
    spec_fields = {field.name for field in dataclasses.fields(ParcelSpec)}
    parts_fields = {field.name for field in dataclasses.fields(ParcelParts)}
    derived = parts_fields - spec_fields
    assert derived == {"heavy"}, "parts must carry derived fields the constructor never accepts"
    assert "heavy" not in spec_fields


def test_parts_record_is_total() -> None:
    for field in dataclasses.fields(ParcelParts):
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING


def test_parts_module_never_touches_specs() -> None:
    source = (_ROOT / "parts.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    spec_touches = {name for name in imported | referenced if name.endswith("Spec")}
    assert not spec_touches, f"parts is outbound-only; it must never touch specs: {spec_touches}"
