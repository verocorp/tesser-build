import pytest

from catalog.money import Money, MoneyAmount, MoneyCurrency, MoneySpec


def _spec(amount: str, currency: str = "USD") -> MoneySpec:
    return MoneySpec(amount=amount, currency=currency)


def test_equality_across_representations() -> None:
    a = Money(_spec("1.5"))
    b = Money(_spec("1.50"))
    assert a == b
    assert hash(a) == hash(b)
    assert a != Money(_spec("1.5", "EUR"))
    assert a != Money(_spec("2.0"))


def test_amount_equality_across_representations() -> None:
    assert MoneyAmount("1.5") == MoneyAmount("1.50")
    assert MoneyAmount("1.5") != MoneyAmount("2.0")


def test_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="currency is required"):
        Money(_spec("1.00", ""))
    with pytest.raises(ValueError, match="invalid amount"):
        Money(_spec("abc"))
    with pytest.raises(ValueError, match="must not be negative"):
        Money(_spec("-1.00"))


def test_components_are_value_objects() -> None:
    m = Money(_spec("1.50"))
    assert m.amount == MoneyAmount("1.50")
    assert m.currency == MoneyCurrency("USD")


def test_amount_canonical_round_trip() -> None:
    a = MoneyAmount("1.50")
    assert MoneyAmount(str(a)) == a


def test_currency_canonical_round_trip() -> None:
    c = MoneyCurrency("USD")
    assert MoneyCurrency(str(c)) == c


def test_add_same_currency() -> None:
    assert Money(_spec("1.50")).add(Money(_spec("2.25"))) == Money(_spec("3.75"))


def test_add_rejects_currency_mismatch() -> None:
    with pytest.raises(ValueError, match="cannot add"):
        Money(_spec("1.00", "USD")).add(Money(_spec("1.00", "EUR")))


def test_compound_has_no_conversion_dunders() -> None:
    assert "__str__" not in Money.__dict__
    assert "__int__" not in Money.__dict__
    assert "__float__" not in Money.__dict__
    assert "__bytes__" not in Money.__dict__
