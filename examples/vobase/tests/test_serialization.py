from decimal import Decimal

from vobase.serialization import canonical_decimal, canonical_str


def test_canonical_str_is_identity() -> None:
    assert canonical_str("USD") == "USD"
    assert canonical_str("usd") == "usd"
    assert canonical_str("") == ""


def test_canonical_decimal_matches_str_of_decimal() -> None:
    assert canonical_decimal(Decimal("0")) == "0"
    assert canonical_decimal(Decimal("1.50")) == "1.50"
    assert canonical_decimal(Decimal("-1.00")) == "-1.00"
