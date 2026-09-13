from __future__ import annotations

import enum
import json
import typing

import tesser.application as ts

import ordering.application.snapshots as snapshots
import ordering.domain as domain


class ConfirmOrderRequest(ts.Request):

    def __init__(self, order: domain.Order) -> None:
        self.order = order


class ConfirmOrderRequestSnapshot(ts.Serde):

    def serialize(self, confirm_order_request: ConfirmOrderRequest) -> bytes:
        return snapshots.OrderSnapshot().serialize(confirm_order_request.order)

    def deserialize(self, buf: bytes) -> ConfirmOrderRequest:
        return ConfirmOrderRequest(order=snapshots.OrderSnapshot().deserialize(buf))


class StartConfirmOrderOutcome(enum.Enum):
    STARTED = "started"


class StartConfirmOrderResponse(ts.Response):

    def __init__(self, outcome: StartConfirmOrderOutcome, order_id: str) -> None:
        self.outcome = outcome
        self.order_id = order_id


class ConfirmOrderOutcome(enum.Enum):
    CONFIRMED = "confirmed"
    PRODUCT_PRICE_NOT_FOUND = "product_price_not_found"
    ALREADY_STARTED = "already_started"


class ConfirmedOrder(ts.Response):

    def __init__(self, total_cents: int) -> None:
        self.total_cents = total_cents


class ConfirmOrderResponse(ts.Response):

    def __init__(
        self,
        outcome: ConfirmOrderOutcome,
        order_id: str,
        confirmed_orders: tuple[ConfirmedOrder, ...],
        reasons: tuple[str, ...],
    ) -> None:
        self.outcome = outcome
        self.order_id = order_id
        self.confirmed_orders = confirmed_orders
        self.reasons = reasons


class ConfirmOrderResponseSnapshot(ts.Serde):

    def serialize(self, confirm_order_response: ConfirmOrderResponse) -> bytes:
        return json.dumps(
            {
                "outcome": confirm_order_response.outcome.value,
                "order_id": confirm_order_response.order_id,
                "confirmed_orders": [
                    {"total_cents": confirmed_order.total_cents}
                    for confirmed_order in confirm_order_response.confirmed_orders
                ],
                "reasons": list(confirm_order_response.reasons),
            }
        ).encode()

    def deserialize(self, buf: bytes) -> ConfirmOrderResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and snapshot["order_id"]
            and isinstance(snapshot.get("confirmed_orders"), list)
            and isinstance(snapshot.get("reasons"), list)
            and all(isinstance(reason, str) and reason for reason in snapshot["reasons"])
            and all(
                isinstance(confirmed_order, dict)
                and isinstance(confirmed_order.get("total_cents"), int)
                and not isinstance(confirmed_order.get("total_cents"), bool)
                and confirmed_order["total_cents"] >= 0
                for confirmed_order in snapshot["confirmed_orders"]
            )
        ):
            raise ValueError(
                "a confirm order response is an outcome, an order_id, "
                "the orders it confirmed, and its reasons"
            )
        try:
            confirm_order_outcome = ConfirmOrderOutcome(snapshot.get("outcome"))
        except ValueError as value_error:
            raise ValueError("a confirm order response names a confirming outcome") from value_error
        match confirm_order_outcome:
            case ConfirmOrderOutcome.CONFIRMED:
                expected = 1
            case ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND | ConfirmOrderOutcome.ALREADY_STARTED:
                expected = 0
            case _ as never:
                typing.assert_never(never)
        if len(snapshot["confirmed_orders"]) != expected:
            raise ValueError(
                f"a {confirm_order_outcome.value} order carries {expected} confirmed order(s)"
            )
        return ConfirmOrderResponse(
            outcome=confirm_order_outcome,
            order_id=snapshot["order_id"],
            confirmed_orders=tuple(
                ConfirmedOrder(total_cents=confirmed_order["total_cents"])
                for confirmed_order in snapshot["confirmed_orders"]
            ),
            reasons=tuple(snapshot["reasons"]),
        )


class OrderOrchestratorRunner(ts.Relay, typing.Protocol):

    async def start_confirm_order(
        self, confirm_order_request: ConfirmOrderRequest
    ) -> StartConfirmOrderResponse: ...

    async def run_confirm_order(
        self, confirm_order_request: ConfirmOrderRequest
    ) -> ConfirmOrderResponse: ...
