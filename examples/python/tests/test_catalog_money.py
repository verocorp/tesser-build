import pytest

from catalog.money import Money, MoneySpec


def _money(amount: str, currency: str = "USD") -> Money:
    return Money.from_spec(MoneySpec(amount=amount, currency=currency))


def test_equality_across_representations() -> None:
    a = _money("1.5")
    b = _money("1.50")
    assert a == b
    assert hash(a) == hash(b)
    assert a != _money("1.5", "EUR")
    assert a != _money("2.0")


def test_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="currency is required"):
        _money("1.00", "")
    with pytest.raises(ValueError, match="invalid amount"):
        _money("abc")
    with pytest.raises(ValueError, match="must not be negative"):
        _money("-1.00")


def test_add_same_currency() -> None:
    assert _money("1.50").add(_money("2.25")) == _money("3.75")


def test_add_rejects_currency_mismatch() -> None:
    with pytest.raises(ValueError, match="cannot add"):
        _money("1.00", "USD").add(_money("1.00", "EUR"))


def test_str_is_display() -> None:
    assert str(_money("1.5")) == "1.50 USD"
