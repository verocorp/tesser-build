from __future__ import annotations

import ast
import pathlib

import parcel.domain.parcel as parcel

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
