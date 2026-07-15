"""A field typed as a proper value object (not a raw primitive) -- should-pass.

Money is deliberately NOT a @dataclass (so it is out of scope for the
dataclass-decorator hook entirely) -- an ordinary hand-built immutable VO,
so the only thing under test is whether OrderLine.price:Money gets a
false-positive PRIMITIVE finding. It must not.
"""
from dataclasses import dataclass


class Money:
    def __init__(self, amount: int, currency: str) -> None:
        self._amount = amount
        self._currency = currency

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Money)
            and self._amount == other._amount
            and self._currency == other._currency
        )

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))


@dataclass(frozen=True)
class OrderLine:
    price: Money  # VO type, not primitive -- should-pass


ol = OrderLine(price=Money(amount=100, currency="USD"))  # valid construction call
