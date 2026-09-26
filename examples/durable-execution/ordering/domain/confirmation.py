from __future__ import annotations

import enum

import tesser.domain as ts

import ordering.domain.kernel as kernel
import tesser.errors as errors


class PriceQuoteSpec(ts.Spec):
    def __init__(self, outcome: str, prices: tuple[kernel.PriceSpec, ...]) -> None:
        self.outcome = outcome
        self.prices = prices


class PriceQuote(ts.ValueObject):
    _prices: tuple[kernel.Price, ...]

    def __init__(self, spec: PriceQuoteSpec) -> None:
        if not (
            (spec.outcome == "priced" and len(spec.prices) == 1)
            or (spec.outcome == "price_not_found" and not spec.prices)
        ):
            raise errors.invalid(
                "invalid_quote", "a priced product has one price; an unpriced product has none"
            )
        object.__setattr__(
            self, "_prices", tuple(kernel.Price(price_spec) for price_spec in spec.prices)
        )

    @property
    def prices(self) -> tuple[kernel.Price, ...]:
        return self._prices


class OrderConfirmationOutcome(ts.Outcome):
    CONFIRMED = enum.auto()
    PRICE_NOT_FOUND = enum.auto()


class OrderConfirmationSpec(ts.Spec):
    def __init__(self, order_id: str, quantity: int) -> None:
        self.order_id = order_id
        self.quantity = quantity


class OrderConfirmation(ts.AggregateRoot):
    def __init__(self, spec: OrderConfirmationSpec) -> None:
        self._id = kernel.OrderId(spec.order_id)
        self._quantity = kernel.Quantity(spec.quantity)
        self._totals: tuple[kernel.Price, ...] = ()

    @property
    def identity(self) -> kernel.OrderId:
        return self._id

    @property
    def total(self) -> kernel.Price:
        if not self._totals:
            raise errors.conflict("order_not_confirmed", "an unconfirmed order has no total")
        return self._totals[0]

    def confirm(self, price_quote_spec: PriceQuoteSpec) -> OrderConfirmationOutcome:
        if self._totals:
            raise errors.conflict(
                "order_already_confirmed", "a confirmed order cannot be priced again"
            )
        price_quote = PriceQuote(price_quote_spec)
        if not price_quote.prices:
            return OrderConfirmationOutcome.PRICE_NOT_FOUND
        self._totals = (price_quote.prices[0].times(self._quantity),)
        return OrderConfirmationOutcome.CONFIRMED
