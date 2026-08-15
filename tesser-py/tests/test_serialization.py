from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from tesser.serialization import (
    canonical_bytes,
    canonical_datetime,
    canonical_decimal,
    canonical_float,
    canonical_int,
    canonical_str,
)


def test_primitive_canonicals_are_identity() -> None:
    assert canonical_str("USD") == "USD"
    assert canonical_int(7) == 7
    assert canonical_float(1.5) == 1.5
    assert canonical_bytes(b"\x00\x01") == b"\x00\x01"


def test_decimal_canonical_is_its_exact_text() -> None:
    assert canonical_decimal(Decimal("10.10")) == "10.10"
    assert canonical_decimal(Decimal("10.1")) == "10.1"


def test_datetime_canonical_is_utc_isoformat_with_microseconds() -> None:
    value = datetime(2026, 8, 15, 14, 30, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert canonical_datetime(value) == "2026-08-15T19:30:00.000000+00:00"


def test_a_naive_datetime_has_no_canonical_form() -> None:
    with pytest.raises(ValueError):
        canonical_datetime(datetime(2026, 8, 15, 14, 30, 0))
