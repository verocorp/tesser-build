import re

import pytest

from vo.amount import Amount


def test_construction_validates() -> None:
    with pytest.raises(ValueError, match=re.escape("amount must not be negative: -1")):
        Amount(-1)
    assert Amount(0).value() == 0
    assert Amount(1).value() == 1


def test_add() -> None:
    assert Amount(2).add(Amount(3)) == Amount(5)


def test_equality() -> None:
    assert Amount(2) == Amount(2)
    assert Amount(2) != Amount(3)
    assert hash(Amount(2)) == hash(Amount(2))
