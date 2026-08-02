from decimal import Decimal

import pytest

from vobase.serialization import canonical_decimal, canonical_str


def test_canonical_str_is_identity() -> None:
    assert canonical_str("USD") == "USD"
    assert canonical_str("usd") == "usd"
    assert canonical_str("") == ""


def test_canonical_decimal_is_plain_form() -> None:
    assert canonical_decimal(Decimal("0")) == "0"
    assert canonical_decimal(Decimal("1.50")) == "1.50"
    assert canonical_decimal(Decimal("-1.00")) == "-1.00"
    assert canonical_decimal(Decimal("1E-7")) == "0.0000001"
    assert canonical_decimal(Decimal("1E+2")) == "100"


def test_canonical_decimal_bounds_its_output() -> None:
    assert canonical_decimal(Decimal("1E+40")) == "1" + "0" * 40
    assert canonical_decimal(Decimal("1E-40")) == "0." + "0" * 39 + "1"
    for bad in ("1E+41", "1E-41", "1E+50000000", "Infinity", "-Infinity", "NaN"):
        with pytest.raises(ValueError, match="no canonical decimal form"):
            canonical_decimal(Decimal(bad))
