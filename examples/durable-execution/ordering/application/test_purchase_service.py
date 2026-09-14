from __future__ import annotations

import asyncio

import tesser.testing as ts
import pytest

import ordering.application as application
import ordering.application.relays as relays
import ordering.client as client


@ts.fake
class FakePayForOrderRelay(relays.PayForOrderRelay):

    def __init__(self) -> None:
        self.ran: list[relays.PayForOrderRequest] = []

    async def run_pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse:
        self.ran.append(pay_for_order_request)
        return relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.PAID,
            order_id=str(pay_for_order_request.order.identity),
            purchases=(
                relays.Purchase(
                    total_cents=250 * int(pay_for_order_request.order.quantity),
                    payment_reference=f"pay-{pay_for_order_request.order.identity}",
                ),
            ),
            reasons=(),
        )


@ts.fake
class FakeUnconfirmedPayForOrderRelay(relays.PayForOrderRelay):

    async def run_pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse:
        return relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED,
            order_id=str(pay_for_order_request.order.identity),
            purchases=(),
            reasons=(f"no price for sku {pay_for_order_request.order.sku!s}",),
        )


@ts.fake
class FakeDecliningPayForOrderRelay(relays.PayForOrderRelay):

    async def run_pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse:
        return relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.PAYMENT_DECLINED,
            order_id=str(pay_for_order_request.order.identity),
            purchases=(),
            reasons=("the processor declined the charge",),
        )


@ts.fake
class FakeStartedPayForOrderRelay(relays.PayForOrderRelay):

    async def run_pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse:
        return relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.ALREADY_STARTED,
            order_id=str(pay_for_order_request.order.identity),
            purchases=(),
            reasons=(),
        )


@ts.helper
def make_order_payment_request(
    order_id: str = "o1",
    sku: str = "widget",
    quantity: int = 2,
    payment_method: str = "card-4242",
) -> client.MakeOrderPaymentRequest:
    return client.MakeOrderPaymentRequest(
        order_id=order_id, sku=sku, quantity=quantity, payment_method=payment_method
    )


class TestPurchaseService:

    def test_paying_answers_the_order_id_the_total_and_the_payment_reference(self) -> None:
        make_order_payment_response = asyncio.run(
            application.PurchaseService(FakePayForOrderRelay()).make_order_payment(
                make_order_payment_request(quantity=3)
            )
        )
        assert make_order_payment_response.order_id == "o1"
        assert make_order_payment_response.total_cents == 750
        assert make_order_payment_response.payment_reference == "pay-o1"

    def test_paying_runs_the_orchestrator_for_the_order_it_built_and_waits(self) -> None:
        fake_pay_for_order_relay = FakePayForOrderRelay()
        asyncio.run(
            application.PurchaseService(fake_pay_for_order_relay).make_order_payment(
                make_order_payment_request(order_id="o2", sku="gadget", quantity=3)
            )
        )
        assert [
            (str(r.order.identity), str(r.order.sku), int(r.order.quantity))
            for r in fake_pay_for_order_relay.ran
        ] == [("o2", "gadget", 3)]

    def test_paying_carries_the_payment_method_the_caller_named(self) -> None:
        fake_pay_for_order_relay = FakePayForOrderRelay()
        asyncio.run(
            application.PurchaseService(fake_pay_for_order_relay).make_order_payment(
                make_order_payment_request(payment_method="card-1234")
            )
        )
        assert [str(r.payment_method) for r in fake_pay_for_order_relay.ran] == [
            "card-1234"
        ]

    def test_an_empty_payment_method_is_refused_before_the_engine(self) -> None:
        fake_pay_for_order_relay = FakePayForOrderRelay()
        with pytest.raises(client.OrderRejected) as excinfo:
            asyncio.run(
                application.PurchaseService(fake_pay_for_order_relay).make_order_payment(
                    make_order_payment_request(payment_method="")
                )
            )
        assert excinfo.value.message == "a payment method is never empty"
        assert fake_pay_for_order_relay.ran == []

    def test_an_order_that_was_not_confirmed_is_the_situation_of_that_name(self) -> None:
        with pytest.raises(client.OrderNotConfirmed) as excinfo:
            asyncio.run(
                application.PurchaseService(
                    FakeUnconfirmedPayForOrderRelay()
                ).make_order_payment(make_order_payment_request(sku="nothing"))
            )
        assert excinfo.value.message == "no price for sku nothing"

    def test_a_declined_payment_is_the_situation_of_that_name(self) -> None:
        with pytest.raises(client.PaymentDeclined) as excinfo:
            asyncio.run(
                application.PurchaseService(
                    FakeDecliningPayForOrderRelay()
                ).make_order_payment(make_order_payment_request())
            )
        assert excinfo.value.message == "the processor declined the charge"

    def test_an_order_already_started_is_the_situation_of_that_name(self) -> None:
        with pytest.raises(client.OrderAlreadyStarted) as excinfo:
            asyncio.run(
                application.PurchaseService(
                    FakeStartedPayForOrderRelay()
                ).make_order_payment(make_order_payment_request())
            )
        assert excinfo.value.message == "the order was already started"
