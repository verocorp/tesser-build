from __future__ import annotations

import enum

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


class PaymentMethod(ts.ValueObject):
    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_payment_method", "a payment method is never empty")
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
    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class PurchaseConfirmationSpec(ts.Spec):
    def __init__(self, order_id: str, totals: tuple[kernel.PriceSpec, ...]) -> None:
        self.order_id = order_id
        self.totals = totals


class PurchaseConfirmation(ts.ValueObject):
    _order_id: kernel.OrderId
    _totals: tuple[kernel.Price, ...]

    def __init__(self, spec: PurchaseConfirmationSpec) -> None:
        if len(spec.totals) > 1:
            raise errors.invalid(
                "invalid_confirmation",
                "an order confirmation supplies at most one total",
            )
        object.__setattr__(self, "_order_id", kernel.OrderId(spec.order_id))
        object.__setattr__(
            self, "_totals", tuple(kernel.Price(price_spec) for price_spec in spec.totals)
        )

    @property
    def order_id(self) -> kernel.OrderId:
        return self._order_id

    @property
    def totals(self) -> tuple[kernel.Price, ...]:
        return self._totals


class PaymentResultSpec(ts.Spec):
    def __init__(self, outcome: str, payments: tuple[PaymentSpec, ...]) -> None:
        self.outcome = outcome
        self.payments = payments


class PaymentResult(ts.ValueObject):
    _payments: tuple[Payment, ...]

    def __init__(self, spec: PaymentResultSpec) -> None:
        if not (
            (spec.outcome == "taken" and len(spec.payments) == 1)
            or (spec.outcome == "declined" and not spec.payments)
        ):
            raise errors.invalid(
                "invalid_payment_result",
                "a taken payment has one receipt; a declined payment has none",
            )
        object.__setattr__(
            self, "_payments", tuple(Payment(payment_spec) for payment_spec in spec.payments)
        )

    @property
    def payments(self) -> tuple[Payment, ...]:
        return self._payments


class PurchaseConfirmationOutcome(ts.Outcome):
    CONFIRMED = enum.auto()
    ORDER_NOT_CONFIRMED = enum.auto()


class PurchaseSettlementOutcome(ts.Outcome):
    PAID = enum.auto()
    DECLINED = enum.auto()


class Purchase(ts.AggregateRoot):
    def __init__(self, spec: PurchaseSpec) -> None:
        self._id = kernel.OrderId(spec.order_id)
        self._totals: tuple[kernel.Price, ...] = ()
        self._payments: tuple[Payment, ...] = ()

    @property
    def identity(self) -> kernel.OrderId:
        return self._id

    @property
    def total(self) -> kernel.Price:
        if not self._totals:
            raise errors.conflict("purchase_not_confirmed", "an unconfirmed purchase has no total")
        return self._totals[0]

    @property
    def payment(self) -> Payment:
        if not self._payments:
            raise errors.conflict("purchase_not_paid", "an unpaid purchase has no payment")
        return self._payments[0]

    def confirm(
        self, purchase_confirmation_spec: PurchaseConfirmationSpec
    ) -> PurchaseConfirmationOutcome:
        if self._totals:
            raise errors.conflict(
                "purchase_already_confirmed", "a confirmed purchase cannot change its total"
            )
        purchase_confirmation = PurchaseConfirmation(purchase_confirmation_spec)
        if purchase_confirmation.order_id != self._id:
            raise errors.conflict(
                "priced_another_order",
                f"order {str(self._id)!r} cannot be purchased with a pricing of order {str(purchase_confirmation.order_id)!r}",
            )
        if not purchase_confirmation.totals:
            return PurchaseConfirmationOutcome.ORDER_NOT_CONFIRMED
        self._totals = purchase_confirmation.totals
        return PurchaseConfirmationOutcome.CONFIRMED

    def settle(self, payment_result_spec: PaymentResultSpec) -> PurchaseSettlementOutcome:
        if not self._totals:
            raise errors.conflict(
                "purchase_not_confirmed", "an unconfirmed purchase cannot be paid"
            )
        if self._payments:
            raise errors.conflict("purchase_already_paid", "a paid purchase cannot be paid again")
        payment_result = PaymentResult(payment_result_spec)
        if not payment_result.payments:
            return PurchaseSettlementOutcome.DECLINED
        payment = payment_result.payments[0]
        if payment.order_id != self._id:
            raise errors.conflict(
                "payment_for_another_order",
                f"a payment for order {payment.order_id!s} does not settle order {self._id!s}",
            )
        if payment.amount != self._totals[0]:
            raise errors.conflict(
                "payment_mismatch",
                f"a payment of {int(payment.amount)} cents does not settle a purchase of {int(self._totals[0])} cents",
            )
        self._payments = (payment,)
        return PurchaseSettlementOutcome.PAID
