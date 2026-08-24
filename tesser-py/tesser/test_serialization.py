import datetime
import decimal

import pytest

import tesser.serialization as serialization


def test_primitive_canonicals_are_identity() -> None:
    assert serialization.canonical_str("USD") == "USD"
    assert serialization.canonical_int(7) == 7
    assert serialization.canonical_float(1.5) == 1.5
    assert serialization.canonical_bytes(b"\x00\x01") == b"\x00\x01"


def test_decimal_canonical_is_its_exact_text() -> None:
    assert serialization.canonical_decimal(decimal.Decimal("10.10")) == "10.10"
    assert serialization.canonical_decimal(decimal.Decimal("10.1")) == "10.1"


def test_datetime_canonical_is_utc_isoformat_with_microseconds() -> None:
    value = datetime.datetime(2026, 8, 15, 14, 30, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))
    assert serialization.canonical_datetime(value) == "2026-08-15T19:30:00.000000+00:00"


def test_a_naive_datetime_has_no_canonical_form() -> None:
    with pytest.raises(ValueError):
        serialization.canonical_datetime(datetime.datetime(2026, 8, 15, 14, 30, 0))
