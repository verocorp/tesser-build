import pytest

from catalog.sku import SKU


def test_equality() -> None:
    assert SKU("TSHIRT-BLK-M") == SKU("TSHIRT-BLK-M")
    assert SKU("TSHIRT-BLK-M") != SKU("TSHIRT-WHT-M")


@pytest.mark.parametrize("bad", ["", "ab", "tshirt", "TS_HIRT", "TOO-LONG-A-SKU-VALUE-X"])
def test_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError, match="invalid SKU"):
        SKU(bad)


def test_str_is_display() -> None:
    assert str(SKU("TSHIRT-BLK-M")) == "TSHIRT-BLK-M"
