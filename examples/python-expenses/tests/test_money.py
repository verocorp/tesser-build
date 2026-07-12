import pytest

from expenses.money import Money, MoneySpec


def test_money_equality() -> None:
    a = Money.from_spec(MoneySpec("1.5", "USD"))
    b = Money.from_spec(MoneySpec("1.50", "USD"))
    assert a == b  # equal logical values, across representations
    assert hash(a) == hash(b)


def test_money_inequality_different_amount() -> None:
    a = Money.from_spec(MoneySpec("1.50", "USD"))
    b = Money.from_spec(MoneySpec("2.00", "USD"))
    assert a != b


def test_money_inequality_different_currency() -> None:
    a = Money.from_spec(MoneySpec("1.50", "USD"))
    b = Money.from_spec(MoneySpec("1.50", "EUR"))
    assert a != b


def test_money_rejects_missing_currency() -> None:
    with pytest.raises(ValueError, match="currency is required"):
        Money.from_spec(MoneySpec("1.00", ""))


def test_money_rejects_invalid_currency_code() -> None:
    with pytest.raises(ValueError, match="invalid currency code"):
        Money.from_spec(MoneySpec("1.00", "US"))


def test_money_rejects_invalid_amount() -> None:
    with pytest.raises(ValueError, match="invalid money amount"):
        Money.from_spec(MoneySpec("not-a-number", "USD"))


def test_money_add_same_currency() -> None:
    a = Money.from_spec(MoneySpec("10.00", "USD"))
    b = Money.from_spec(MoneySpec("5.25", "USD"))
    assert a.add(b) == Money.from_spec(MoneySpec("15.25", "USD"))


def test_money_add_rejects_mismatched_currency() -> None:
    a = Money.from_spec(MoneySpec("10.00", "USD"))
    b = Money.from_spec(MoneySpec("5.25", "EUR"))
    with pytest.raises(ValueError, match="cannot add"):
        a.add(b)


def test_money_str() -> None:
    m = Money.from_spec(MoneySpec("10.00", "USD"))
    assert str(m) == "10.00 USD"
