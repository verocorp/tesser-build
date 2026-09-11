from __future__ import annotations

import tesser.domain as ts

import ordering.domain.kernel as kernel
import tesser.errors as errors
import tesser.serialization as serialization


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

    _order_id: kernel.OrderId
    _reference: PaymentReference
    _amount: kernel.Price

    def __init__(self, spec: PaymentSpec) -> None:
        object.__setattr__(self, "_order_id", kernel.OrderId(spec.order_id))
        object.__setattr__(self, "_reference", PaymentReference(spec.reference))
        object.__setattr__(self, "_amount", kernel.Price(kernel.PriceSpec(cents=spec.cents)))

    @property
    def order_id(self) -> kernel.OrderId:
        return self._order_id

    @property
    def reference(self) -> PaymentReference:
        return self._reference

    @property
    def amount(self) -> kernel.Price:
        return self._amount


class PurchaseSpec(ts.Spec):

    def __init__(self, order_id: str, priced_order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.priced_order_id = priced_order_id
        self.total_cents = total_cents


class Purchase(ts.AggregateRoot):

    def __init__(self, spec: PurchaseSpec) -> None:
        self._id = kernel.OrderId(spec.order_id)
        if kernel.OrderId(spec.priced_order_id) != self._id:
            raise errors.conflict(
                "priced_another_order",
                f"order {spec.order_id!r} cannot be purchased with a pricing of order {spec.priced_order_id!r}",
            )
        self._total = kernel.Price(kernel.PriceSpec(cents=spec.total_cents))

    @property
    def identity(self) -> kernel.OrderId:
        return self._id

    @property
    def total(self) -> kernel.Price:
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
