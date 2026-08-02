from decimal import Decimal, localcontext

import pytest

from vobase.money import Money, MoneyAmount, MoneyCurrency, MoneySpec


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


def test_zero_amount_is_valid() -> None:
    assert str(MoneyAmount("0")) == "0"
    assert MoneyAmount("0.50") == MoneyAmount("0.5")


def test_zero_has_one_canonical_form() -> None:
    assert MoneyAmount("-0") == MoneyAmount("0")
    assert str(MoneyAmount("-0")) == "0"
    assert str(MoneyAmount("0.00")) == "0"


def test_rejects_invalid() -> None:
    with pytest.raises(ValueError, match=r"^currency is required$"):
        Money(_spec("1.00", ""))
    with pytest.raises(ValueError, match=r"^currency is required$"):
        Money(_spec("1.00", " "))
    with pytest.raises(ValueError, match="invalid amount"):
        Money(_spec("abc"))
    with pytest.raises(ValueError, match="must not be negative"):
        Money(_spec("-1.00"))


def test_rejects_non_plain_decimal_forms() -> None:
    for bad in ("NaN", "sNaN", "Infinity", "-Infinity", "1_000", " 1.5 ", "+5", "1e2", "1E+2", ".5", "1.", "٣٤", "１２"):
        with pytest.raises(ValueError, match="invalid amount"):
            MoneyAmount(bad)


def test_rejects_out_of_range_amounts() -> None:
    assert str(MoneyAmount("1" + "0" * 40)) == "1" + "0" * 40
    with pytest.raises(ValueError, match="amount out of range"):
        MoneyAmount("1" + "0" * 41)
    with pytest.raises(ValueError, match="amount out of range"):
        MoneyAmount("0." + "0" * 41 + "1")


def test_add_never_silently_rounds() -> None:
    a = MoneyAmount("1.50")
    assert a.add(MoneyAmount("0")) == a
    assert str(a.add(MoneyAmount("0"))) == "1.50"
    big = MoneyAmount("1234567890123456789012345678.99")
    with pytest.raises(ValueError, match=r"^amount arithmetic exceeds supported precision$"):
        big.add(MoneyAmount("0"))
    long_zeros = MoneyAmount("1." + "0" * 30)
    with pytest.raises(ValueError, match=r"^amount arithmetic exceeds supported precision$"):
        long_zeros.add(MoneyAmount("0"))
    exactly_28 = MoneyAmount("1" * 28)
    assert exactly_28.add(MoneyAmount("0")) == exactly_28
    exactly_29 = MoneyAmount("1" * 29)
    with pytest.raises(ValueError, match=r"^amount arithmetic exceeds supported precision$"):
        exactly_29.add(MoneyAmount("0"))


def test_add_ignores_ambient_decimal_context() -> None:
    with localcontext() as ctx:
        ctx.prec = 4
        assert Money(_spec("123.45")).add(Money(_spec("0.01"))) == Money(_spec("123.46"))


def test_currency_is_stored_normalized() -> None:
    assert MoneyCurrency(" USD ") == MoneyCurrency("USD")
    assert str(MoneyCurrency(" USD ")) == "USD"


def test_currency_must_be_three_uppercase_letters() -> None:
    for bad in ("usd", "US$", "USDX", "US", "USD\nEUR", "US D"):
        with pytest.raises(ValueError, match="currency must be 3 uppercase letters"):
            MoneyCurrency(bad)


def test_tiny_amount_round_trips_through_add() -> None:
    tiny = MoneyAmount("0.0000001")
    assert str(tiny) == "0.0000001"
    assert tiny.add(MoneyAmount("0")) == tiny
    assert MoneyAmount(str(tiny)) == tiny


def test_components_are_value_objects() -> None:
    m = Money(_spec("1.50"))
    assert m.amount() == MoneyAmount("1.50")
    assert m.currency() == MoneyCurrency("USD")


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


def test_immutable_after_construction() -> None:
    m = Money(_spec("1.50"))
    with pytest.raises(AttributeError, match=r"Money is immutable: cannot set '_amount'"):
        m._amount = MoneyAmount("9")
    with pytest.raises(AttributeError, match=r"Money is immutable: cannot delete '_currency'"):
        del m._currency
    a = MoneyAmount("1.50")
    with pytest.raises(AttributeError, match=r"MoneyAmount is immutable: cannot set '_value'"):
        a._value = Decimal("9")
    assert m == Money(_spec("1.50"))


def test_compound_has_no_conversion_dunders() -> None:
    assert "__str__" not in Money.__dict__
    assert "__int__" not in Money.__dict__
    assert "__float__" not in Money.__dict__
    assert "__bytes__" not in Money.__dict__
