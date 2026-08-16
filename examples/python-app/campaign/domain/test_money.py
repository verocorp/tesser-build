from __future__ import annotations

import pytest

import campaign.domain.money as money
from tesser.errors import DomainError, Kind


def test_a_money_amount_round_trips_through_its_canonical_exit() -> None:
    amount = money.MoneyAmount("1.50")

    assert money.MoneyAmount(str(amount)) == amount


def test_a_money_amount_keeps_the_scale_it_was_written_with() -> None:
    assert str(money.MoneyAmount("1.50")) == "1.50"
    assert str(money.MoneyAmount("1.5")) == "1.5"


def test_money_amounts_that_are_numerically_equal_are_the_same_value() -> None:
    a = money.MoneyAmount("1.5")
    b = money.MoneyAmount("1.50")

    assert a == b
    assert hash(a) == hash(b)


def test_a_money_amount_of_zero_is_admitted() -> None:
    assert money.MoneyAmount("0") == money.MoneyAmount("0.00")


@pytest.mark.parametrize("value", ["", "abc", "1.2.3", "1,50", "$1.00", "one"])
def test_a_money_amount_that_is_not_a_number_is_rejected(value: str) -> None:
    with pytest.raises(DomainError) as caught:
        money.MoneyAmount(value)

    assert caught.value.kind is Kind.VALIDATION
    assert caught.value.code == "invalid_budget_amount"
    assert "is not a number" in caught.value.message


@pytest.mark.parametrize("value", ["-0.01", "-1", "-1000000"])
def test_a_negative_money_amount_is_rejected(value: str) -> None:
    with pytest.raises(DomainError) as caught:
        money.MoneyAmount(value)

    assert caught.value.code == "invalid_budget_amount"
    assert "must not be negative" in caught.value.message


def test_a_money_currency_round_trips_through_its_canonical_exit() -> None:
    currency = money.MoneyCurrency("USD")

    assert money.MoneyCurrency(str(currency)) == currency


def test_different_currency_codes_are_different_values() -> None:
    assert money.MoneyCurrency("USD") != money.MoneyCurrency("EUR")


@pytest.mark.parametrize("value", ["", "us", "usd", "USDD", "US1", "US", "U S"])
def test_a_currency_that_is_not_three_uppercase_letters_is_rejected(value: str) -> None:
    with pytest.raises(DomainError) as caught:
        money.MoneyCurrency(value)

    assert caught.value.kind is Kind.VALIDATION
    assert caught.value.code == "invalid_budget_currency"


def test_money_hands_back_its_parts_as_value_objects() -> None:
    amount = money.Money("100.00", "USD")

    assert amount.amount == money.MoneyAmount("100.00")
    assert amount.currency == money.MoneyCurrency("USD")


def test_money_with_the_same_parts_is_the_same_value() -> None:
    a = money.Money("100.00", "USD")
    b = money.Money("100.00", "USD")

    assert a == b
    assert hash(a) == hash(b)


def test_money_in_a_different_currency_is_a_different_value() -> None:
    assert money.Money("100.00", "USD") != money.Money("100.00", "EUR")


def test_money_propagates_an_amount_rejection() -> None:
    with pytest.raises(DomainError) as caught:
        money.Money("nope", "USD")

    assert caught.value.code == "invalid_budget_amount"


def test_money_propagates_a_currency_rejection() -> None:
    with pytest.raises(DomainError) as caught:
        money.Money("100.00", "nope")

    assert caught.value.code == "invalid_budget_currency"


def test_money_is_immutable_once_constructed() -> None:
    budget = money.Money("100.00", "USD")

    with pytest.raises(AttributeError):
        setattr(budget, "amount", money.MoneyAmount("1.00"))
