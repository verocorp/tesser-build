from __future__ import annotations

import tesser.domain as ts

import ordering.domain.kernel as kernel
import tesser.errors as errors
import tesser.serialization as serialization


class Sku(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_sku", "a sku is never empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class OrderSpec(ts.Spec):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class Order(ts.AggregateRoot):

    def __init__(self, spec: OrderSpec) -> None:
        self._id = kernel.OrderId(spec.order_id)
        self._sku = Sku(spec.sku)
        self._quantity = kernel.Quantity(spec.quantity)

    @property
    def identity(self) -> kernel.OrderId:
        return self._id

    @property
    def sku(self) -> Sku:
        return self._sku

    @property
    def quantity(self) -> kernel.Quantity:
        return self._quantity

    def total(self, price_spec: kernel.PriceSpec) -> kernel.Price:
        return kernel.Price(price_spec).times(self._quantity)
