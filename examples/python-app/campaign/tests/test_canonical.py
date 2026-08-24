from __future__ import annotations

import ast
import datetime
import decimal

import pytest

import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import tesser.serialization as serialization
import pathlib


def test_canonical_str_is_the_identity_policy() -> None:
    assert serialization.canonical_str("promo") == "promo"


def test_canonical_decimal_is_the_text_policy() -> None:
    assert serialization.canonical_decimal(decimal.Decimal("19.99")) == "19.99"
    assert serialization.canonical_decimal(decimal.Decimal("1.50")) == "1.50"


def test_equal_decimals_may_have_distinct_canonical_forms() -> None:
    a, b = decimal.Decimal("1.5"), decimal.Decimal("1.50")
    assert a == b
    assert serialization.canonical_decimal(a) != serialization.canonical_decimal(b)
    assert decimal.Decimal(serialization.canonical_decimal(a)) == decimal.Decimal(serialization.canonical_decimal(b))


def test_canonical_datetime_is_pinned_to_utc_microseconds() -> None:
    eastern = datetime.timezone(datetime.timedelta(hours=-5))
    value = datetime.datetime(2026, 7, 20, 10, 16, 15, 123456, tzinfo=eastern)
    assert serialization.canonical_datetime(value) == "2026-07-20T15:16:15.123456+00:00"
    assert serialization.canonical_datetime(datetime.datetime(2026, 7, 20, 15, 0, 0, tzinfo=datetime.timezone.utc)) == (
        "2026-07-20T15:00:00.000000+00:00"
    )


def test_canonical_datetime_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        serialization.canonical_datetime(datetime.datetime(2026, 7, 20, 15, 0, 0))


def test_structured_types_define_no_conversion_dunders() -> None:
    for cls in (money.Money, short_link.ShortLink, campaign.Campaign):
        for name in ("__str__", "__int__", "__float__", "__bytes__"):
            assert name not in cls.__dict__, f"{cls.__name__} defines {name}"


def test_every_domain_conversion_dunder_routes_through_a_canonical_helper() -> None:
    domain_dir = pathlib.Path(__file__).resolve().parent.parent / "domain"
    assert domain_dir.is_dir(), f"domain package not found at {domain_dir}"
    dunders = ("__str__", "__int__", "__float__", "__bytes__")
    assert sorted(domain_dir.glob("*.py")), f"no domain modules under {domain_dir}"
    for path in sorted(domain_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name in dunders):
                continue
            calls = {
                call.func.attr
                for call in ast.walk(node)
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            }
            assert any(name.startswith("canonical_") for name in calls), (
                f"{path.name}: {node.name} at line {node.lineno} does not route "
                f"through a serialization.canonical_* helper"
            )
