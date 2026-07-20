from __future__ import annotations

import ast
import pathlib

from parcel import DeclaredValue, ItemCount, LabelDigest, Parcel, ParcelCode, ScannedAt, WeightKg

_CONVERSION_DUNDERS = ("__str__", "__int__", "__float__", "__bytes__")
_ROOT = pathlib.Path(__file__).resolve().parent.parent

_LEAF_EXITS = {
    ParcelCode: "__str__",
    ItemCount: "__int__",
    WeightKg: "__float__",
    LabelDigest: "__bytes__",
    DeclaredValue: "__str__",
    ScannedAt: "__str__",
}


def test_each_leaf_defines_exactly_its_one_matching_exit() -> None:
    for cls, exit_name in _LEAF_EXITS.items():
        defined = [name for name in _CONVERSION_DUNDERS if name in cls.__dict__]
        assert defined == [exit_name], f"{cls.__name__} defines {defined}, expected [{exit_name}]"


def test_the_compound_defines_no_conversion_dunders() -> None:
    for name in _CONVERSION_DUNDERS:
        assert name not in Parcel.__dict__, f"Parcel defines {name}"


def test_every_conversion_dunder_routes_through_a_canonical_helper() -> None:
    tree = ast.parse((_ROOT / "parcel.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in _CONVERSION_DUNDERS):
            continue
        calls = {
            call.func.id
            for call in ast.walk(node)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        }
        assert any(name.startswith("canonical_") for name in calls), (
            f"{node.name} at parcel.py line {node.lineno} does not route "
            f"through a serialization.canonical_* helper"
        )
