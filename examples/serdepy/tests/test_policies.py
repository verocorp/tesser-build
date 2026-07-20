from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from parcel import DeclaredValue, ScannedAt
from serialization import canonical_datetime, canonical_decimal


def test_decimal_policy_is_the_string_form() -> None:
    assert canonical_decimal(Decimal("199.99")) == "199.99"
    assert str(DeclaredValue("1.50")) == "1.50"


def test_equal_decimals_may_have_distinct_canonical_forms() -> None:
    a, b = DeclaredValue("1.5"), DeclaredValue("1.50")
    assert a == b
    assert str(a) != str(b)
    assert DeclaredValue(str(a)) == DeclaredValue(str(b))


def test_datetime_policy_is_aware_utc_iso8601_microseconds() -> None:
    eastern = timezone(timedelta(hours=-5))
    value = datetime(2026, 7, 20, 10, 16, 15, 123456, tzinfo=eastern)
    assert canonical_datetime(value) == "2026-07-20T15:16:15.123456+00:00"
    assert canonical_datetime(datetime(2026, 7, 20, 15, 0, 0, tzinfo=timezone.utc)) == (
        "2026-07-20T15:00:00.000000+00:00"
    )


def test_datetime_policy_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        canonical_datetime(datetime(2026, 7, 20, 15, 0, 0))
    with pytest.raises(ValueError, match="timezone-aware"):
        ScannedAt("2026-07-20T15:00:00")
