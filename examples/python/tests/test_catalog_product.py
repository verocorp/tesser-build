from catalog.money import MoneySpec
from catalog.product import Product, ProductSpec
from catalog.sku import SKU


def _spec() -> ProductSpec:
    return ProductSpec(
        sku="TSHIRT-BLK-M",
        price=MoneySpec(amount="19.99", currency="USD"),
        labels={"color": "black", "size": "M"},
    )


def test_construction() -> None:
    p = Product(_spec())
    assert p.sku == SKU("TSHIRT-BLK-M")
    assert str(p.price) == "19.99 USD"
    assert p.labels.get("color") == "black"


def test_rejects_invalid_child() -> None:
    import pytest

    spec = ProductSpec(
        sku="TSHIRT-BLK-M",
        price=MoneySpec(amount="-1.00", currency="USD"),
        labels={},
    )
    with pytest.raises(ValueError, match="invalid price"):
        Product(spec)


def test_equality_is_identity() -> None:
    a = Product(_spec())
    # Same SKU, different price/labels -> still the same product.
    b = Product(
        ProductSpec(
            sku="TSHIRT-BLK-M",
            price=MoneySpec(amount="29.99", currency="USD"),
            labels={"color": "white"},
        )
    )
    assert a == b
    assert hash(a) == hash(b)
    # Different SKU -> different product.
    c = Product(
        ProductSpec(sku="TSHIRT-WHT-L", price=MoneySpec(amount="19.99", currency="USD"), labels={})
    )
    assert a != c
