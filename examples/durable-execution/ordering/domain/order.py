from __future__ import annotations

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization


class OrderId(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_order_id", "an order id is never empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Sku(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_sku", "a sku is never empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Quantity(ts.ValueObject):

    _value: int

    def __init__(self, value: int) -> None:
        if value < 1:
            raise errors.invalid("quantity_below_one", "an order is for at least one unit")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return serialization.canonical_int(self._value)


class PriceSpec(ts.Spec):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class Price(ts.ValueObject):

    _cents: int

    def __init__(self, spec: PriceSpec) -> None:
        if spec.cents < 0:
            raise errors.invalid("negative_price", "a price is never negative")
        object.__setattr__(self, "_cents", spec.cents)

    def __int__(self) -> int:
        return serialization.canonical_int(self._cents)

    def times(self, quantity: Quantity) -> Price:
        return Price(PriceSpec(cents=self._cents * int(quantity)))


class OrderSpec(ts.Spec):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class Order(ts.AggregateRoot):

    def __init__(self, spec: OrderSpec) -> None:
        self._id = OrderId(spec.order_id)
        self._sku = Sku(spec.sku)
        self._quantity = Quantity(spec.quantity)

    @property
    def identity(self) -> OrderId:
        return self._id

    @property
    def sku(self) -> Sku:
        return self._sku

    @property
    def quantity(self) -> Quantity:
        return self._quantity

    def total(self, spec: PriceSpec) -> Price:
        return Price(spec).times(self._quantity)
