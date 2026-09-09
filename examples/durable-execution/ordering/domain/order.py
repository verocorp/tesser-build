from __future__ import annotations

import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_MAX_UNITS: typing.Final[int] = 1_000_000
_MAX_CENTS: typing.Final[int] = 10**12


class OrderId(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_order_id", "an order id is never empty")
        if value in (".", ".."):
            raise errors.invalid("dotted_order_id", "an order id is never '.' or '..'")
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
        if value > _MAX_UNITS:
            raise errors.invalid("quantity_above_maximum", f"an order is for at most {_MAX_UNITS} units")
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
        if spec.cents > _MAX_CENTS:
            raise errors.invalid("price_above_maximum", f"a price is at most {_MAX_CENTS} cents")
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

    def total(self, price_spec: PriceSpec) -> Price:
        return Price(price_spec).times(self._quantity)


class PaymentReference(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_payment_reference", "a payment reference is never empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class PaymentSpec(ts.Spec):

    def __init__(self, order_id: str, reference: str, cents: int) -> None:
        self.order_id = order_id
        self.reference = reference
        self.cents = cents


class Payment(ts.ValueObject):

    _order_id: OrderId
    _reference: PaymentReference
    _amount: Price

    def __init__(self, spec: PaymentSpec) -> None:
        object.__setattr__(self, "_order_id", OrderId(spec.order_id))
        object.__setattr__(self, "_reference", PaymentReference(spec.reference))
        object.__setattr__(self, "_amount", Price(PriceSpec(cents=spec.cents)))

    @property
    def order_id(self) -> OrderId:
        return self._order_id

    @property
    def reference(self) -> PaymentReference:
        return self._reference

    @property
    def amount(self) -> Price:
        return self._amount


class PurchaseSpec(ts.Spec):

    def __init__(self, order_id: str, priced_order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.priced_order_id = priced_order_id
        self.total_cents = total_cents


class Purchase(ts.AggregateRoot):

    def __init__(self, spec: PurchaseSpec) -> None:
        self._id = OrderId(spec.order_id)
        if OrderId(spec.priced_order_id) != self._id:
            raise errors.conflict(
                "priced_another_order",
                f"order {spec.order_id!r} cannot be purchased with a pricing of order {spec.priced_order_id!r}",
            )
        self._total = Price(PriceSpec(cents=spec.total_cents))

    @property
    def identity(self) -> OrderId:
        return self._id

    @property
    def total(self) -> Price:
        return self._total

    def paid(self, payment_spec: PaymentSpec) -> Payment:
        payment = Payment(payment_spec)
        if payment.order_id != self._id:
            raise errors.conflict(
                "payment_for_another_order",
                f"a payment for order {payment.order_id!s} does not settle order {self._id!s}",
            )
        if payment.amount != self._total:
            raise errors.conflict(
                "payment_mismatch",
                f"a payment of {int(payment.amount)} cents does not settle a purchase of {int(self._total)} cents",
            )
        return payment
