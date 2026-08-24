import re

import pytest

import vo.amount as amount


def test_construction_validates() -> None:
    with pytest.raises(ValueError, match=re.escape("amount must not be negative: -1")):
        amount.Amount(-1)
    assert amount.Amount(0).value() == 0
    assert amount.Amount(1).value() == 1


def test_add() -> None:
    assert amount.Amount(2).add(amount.Amount(3)) == amount.Amount(5)


def test_equality() -> None:
    assert amount.Amount(2) == amount.Amount(2)
    assert amount.Amount(2) != amount.Amount(3)
    assert hash(amount.Amount(2)) == hash(amount.Amount(2))
