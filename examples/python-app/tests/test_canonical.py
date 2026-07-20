from __future__ import annotations

import ast
import pathlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from campaign.domain.campaign import Campaign
from campaign.domain.money import Money, MoneySpec
from campaign.domain.short_link import ShortLink
from serialization import canonical_datetime, canonical_decimal, canonical_str

_CONVERSION_DUNDERS = ("__str__", "__int__", "__float__", "__bytes__")
_DOMAIN_DIR = pathlib.Path(__file__).resolve().parent.parent / "campaign" / "domain"


def test_canonical_str_is_the_identity_policy() -> None:
    assert canonical_str("promo") == "promo"


def test_canonical_decimal_is_the_text_policy() -> None:
    assert canonical_decimal(Decimal("19.99")) == "19.99"
    assert canonical_decimal(Decimal("1.50")) == "1.50"


def test_equal_decimals_may_have_distinct_canonical_forms() -> None:
    a, b = Decimal("1.5"), Decimal("1.50")
    assert a == b
    assert canonical_decimal(a) != canonical_decimal(b)
    assert Decimal(canonical_decimal(a)) == Decimal(canonical_decimal(b))


def test_canonical_datetime_is_pinned_to_utc_microseconds() -> None:
    eastern = timezone(timedelta(hours=-5))
    value = datetime(2026, 7, 20, 10, 16, 15, 123456, tzinfo=eastern)
    assert canonical_datetime(value) == "2026-07-20T15:16:15.123456+00:00"
    assert canonical_datetime(datetime(2026, 7, 20, 15, 0, 0, tzinfo=timezone.utc)) == (
        "2026-07-20T15:00:00.000000+00:00"
    )


def test_canonical_datetime_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        canonical_datetime(datetime(2026, 7, 20, 15, 0, 0))


def test_structured_types_define_no_conversion_dunders() -> None:
    for cls in (Money, ShortLink, Campaign):
        for name in _CONVERSION_DUNDERS:
            assert name not in cls.__dict__, f"{cls.__name__} defines {name}"


def test_every_domain_conversion_dunder_routes_through_a_canonical_helper() -> None:
    for path in sorted(_DOMAIN_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name in _CONVERSION_DUNDERS):
                continue
            calls = {
                call.func.id
                for call in ast.walk(node)
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            }
            assert any(name.startswith("canonical_") for name in calls), (
                f"{path.name}: {node.name} at line {node.lineno} does not route "
                f"through a serialization.canonical_* helper"
            )
