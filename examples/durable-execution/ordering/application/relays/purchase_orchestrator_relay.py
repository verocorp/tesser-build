from __future__ import annotations

import enum  # tesser:debt TB062
import json
import typing

import tesser.application as ts

import ordering.application.snapshots as snapshots
import ordering.domain as domain


class PayForOrderRequest(ts.Request):

    def __init__(self, order: domain.Order, payment_method: domain.PaymentMethod) -> None:
        self.order = order
        self.payment_method = payment_method


class PayForOrderRequestSnapshot(ts.Serde):

    def serialize(self, pay_for_order_request: PayForOrderRequest) -> bytes:
        return json.dumps(
            {
                "order": json.loads(
                    snapshots.OrderSnapshot().serialize(pay_for_order_request.order)
                ),
                "payment_method": str(pay_for_order_request.payment_method),
            }
        ).encode()

    def deserialize(self, buf: bytes) -> PayForOrderRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order"), dict)
            and isinstance(snapshot.get("payment_method"), str)
            and snapshot["payment_method"]
        ):
            raise ValueError("a pay for order request is an order and a payment method")  # tesser:debt TB082
        return PayForOrderRequest(
            order=snapshots.OrderSnapshot().deserialize(json.dumps(snapshot["order"]).encode()),
            payment_method=domain.PaymentMethod(snapshot["payment_method"]),
        )


class PayForOrderOutcome(enum.Enum):  # tesser:debt TB052
    PAID = "paid"
    ORDER_NOT_CONFIRMED = "order_not_confirmed"
    PAYMENT_DECLINED = "payment_declined"
    ALREADY_STARTED = "already_started"


class Purchase(ts.Response):

    def __init__(self, total_cents: int, payment_reference: str) -> None:
        self.total_cents = total_cents
        self.payment_reference = payment_reference


class PayForOrderResponse(ts.Response):

    def __init__(
        self,
        outcome: PayForOrderOutcome,
        order_id: str,
        purchases: tuple[Purchase, ...],
        reasons: tuple[str, ...],
    ) -> None:
        self.outcome = outcome
        self.order_id = order_id
        self.purchases = purchases
        self.reasons = reasons


class PayForOrderResponseSnapshot(ts.Serde):

    def serialize(self, pay_for_order_response: PayForOrderResponse) -> bytes:
        return json.dumps(
            {
                "outcome": pay_for_order_response.outcome.value,
                "order_id": pay_for_order_response.order_id,
                "purchases": [  # tesser:debt TB082
                    {
                        "total_cents": purchase.total_cents,
                        "payment_reference": purchase.payment_reference,
                    }
                    for purchase in pay_for_order_response.purchases
                ],
                "reasons": list(pay_for_order_response.reasons),  # tesser:debt TB082
            }
        ).encode()

    def deserialize(self, buf: bytes) -> PayForOrderResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and snapshot["order_id"]
            and isinstance(snapshot.get("purchases"), list)
            and isinstance(snapshot.get("reasons"), list)
            and all(isinstance(reason, str) and reason for reason in snapshot["reasons"])  # tesser:debt TB082
            and all(  # tesser:debt TB082
                isinstance(purchase, dict)
                and isinstance(purchase.get("total_cents"), int)
                and not isinstance(purchase.get("total_cents"), bool)
                and purchase["total_cents"] >= 0
                and isinstance(purchase.get("payment_reference"), str)
                and purchase["payment_reference"]
                for purchase in snapshot["purchases"]
            )
        ):
            raise ValueError(  # tesser:debt TB082
                "a pay for order response is an outcome, an order_id, "
                "the purchases it paid for, and its reasons"
            )
        try:  # tesser:debt TB082
            pay_for_order_outcome = PayForOrderOutcome(snapshot.get("outcome"))  # tesser:debt TB082 TB085
        except ValueError as value_error:
            raise ValueError("a pay for order response names a paying outcome") from value_error  # tesser:debt TB082
        return PayForOrderResponse(
            outcome=pay_for_order_outcome,
            order_id=snapshot["order_id"],
            purchases=tuple(  # tesser:debt TB082
                Purchase(
                    total_cents=purchase["total_cents"],
                    payment_reference=purchase["payment_reference"],
                )
                for purchase in snapshot["purchases"]
            ),
            reasons=tuple(snapshot["reasons"]),  # tesser:debt TB082
        )


class PurchaseOrchestratorRelay(ts.Relay, typing.Protocol):

    async def run_pay_for_order(
        self, pay_for_order_request: PayForOrderRequest
    ) -> PayForOrderResponse: ...
