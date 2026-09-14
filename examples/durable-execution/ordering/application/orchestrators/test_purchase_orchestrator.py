from __future__ import annotations

import asyncio

import tesser.testing as ts
import pytest

import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays
import ordering.domain as domain
import tesser.errors as errors


@ts.fake
class FakeTakePaymentRelay(relays.TakePaymentRelay):

    def __init__(self, cents_charged: int = 0, order_charged: str = "") -> None:
        self._cents_charged = cents_charged
        self._order_charged = order_charged
        self.taken: list[tuple[str, int, str]] = []

    async def run_take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        self.taken.append(
            (
                take_payment_request.order_id,
                take_payment_request.cents,
                take_payment_request.payment_method,
            )
        )
        order_id = self._order_charged or take_payment_request.order_id
        return relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.TAKEN,
            order_id=order_id,
            payments=(
                relays.Payment(
                    reference=f"pay-{order_id}",
                    cents=self._cents_charged or take_payment_request.cents,
                ),
            ),
            reasons=(),
        )


@ts.fake
class FakeDecliningTakePaymentRelay(relays.TakePaymentRelay):

    async def run_take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.DECLINED,
            order_id=take_payment_request.order_id,
            payments=(),
            reasons=("the processor declined the charge",),
        )


@ts.fake
class FakeConfirmOrderRelay(relays.ConfirmOrderRelay):

    def __init__(self, order_confirmed: str = "") -> None:
        self._order_confirmed = order_confirmed
        self.started: list[str] = []
        self.ran: list[str] = []

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        self.started.append(str(confirm_order_request.order.identity))
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED,
            order_id=str(confirm_order_request.order.identity),
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        self.ran.append(str(confirm_order_request.order.identity))
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id=self._order_confirmed or str(confirm_order_request.order.identity),
            confirmed_orders=(
                relays.ConfirmedOrder(
                    total_cents=250 * int(confirm_order_request.order.quantity)
                ),
            ),
            reasons=(),
        )


@ts.fake
class FakeUnpricedConfirmOrderRelay(relays.ConfirmOrderRelay):

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED,
            order_id=str(confirm_order_request.order.identity),
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND,
            order_id=str(confirm_order_request.order.identity),
            confirmed_orders=(),
            reasons=(f"no price for sku {confirm_order_request.order.sku!s}",),
        )


@ts.fake
class FakeStartedConfirmOrderRelay(relays.ConfirmOrderRelay):

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED,
            order_id=str(confirm_order_request.order.identity),
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.ALREADY_STARTED,
            order_id=str(confirm_order_request.order.identity),
            confirmed_orders=(),
            reasons=(),
        )


@ts.helper
def pay_for_order_request(
    order_id: str = "o1",
    sku: str = "widget",
    quantity: int = 3,
    payment_method: str = "card-4242",
) -> relays.PayForOrderRequest:
    return relays.PayForOrderRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity)),
        payment_method=domain.PaymentMethod(payment_method),
    )


class TestPurchaseOrchestrator:

    def test_paying_answers_the_order_its_total_and_the_payment_taken(self) -> None:
        pay_for_order_response = asyncio.run(
            orchestrators.PurchaseOrchestrator(
                FakeTakePaymentRelay(), FakeConfirmOrderRelay()
            ).pay_for_order(pay_for_order_request())
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAID
        assert pay_for_order_response.order_id == "o1"
        assert pay_for_order_response.purchases[0].total_cents == 750
        assert pay_for_order_response.purchases[0].payment_reference == "pay-o1"

    def test_paying_confirms_the_order_as_a_child_and_then_takes_payment_for_its_total(
        self,
    ) -> None:
        fake_take_payment_relay = FakeTakePaymentRelay()
        fake_confirm_order_relay = FakeConfirmOrderRelay()
        asyncio.run(
            orchestrators.PurchaseOrchestrator(
                fake_take_payment_relay, fake_confirm_order_relay
            ).pay_for_order(pay_for_order_request(order_id="o2", quantity=4))
        )
        assert fake_confirm_order_relay.ran == ["o2"]
        assert fake_confirm_order_relay.started == []
        assert fake_take_payment_relay.taken == [("o2", 1000, "card-4242")]

    def test_the_payment_method_the_caller_named_reaches_the_payment_action(self) -> None:
        fake_take_payment_relay = FakeTakePaymentRelay()
        asyncio.run(
            orchestrators.PurchaseOrchestrator(
                fake_take_payment_relay, FakeConfirmOrderRelay()
            ).pay_for_order(pay_for_order_request(payment_method="card-1234"))
        )
        assert [m for _, _, m in fake_take_payment_relay.taken] == ["card-1234"]

    def test_a_payment_of_another_amount_is_a_fault(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.PurchaseOrchestrator(
                    FakeTakePaymentRelay(cents_charged=700), FakeConfirmOrderRelay()
                ).pay_for_order(pay_for_order_request())
            )
        assert "does not settle" in excinfo.value.message

    def test_an_unconfirmed_child_order_stops_the_act_before_any_payment(self) -> None:
        fake_take_payment_relay = FakeTakePaymentRelay()
        pay_for_order_response = asyncio.run(
            orchestrators.PurchaseOrchestrator(
                fake_take_payment_relay, FakeUnpricedConfirmOrderRelay()
            ).pay_for_order(pay_for_order_request(sku="nothing"))
        )
        assert (
            pay_for_order_response.outcome is relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED
        )
        assert pay_for_order_response.reasons == ("no price for sku nothing",)
        assert fake_take_payment_relay.taken == []

    def test_a_child_already_started_is_the_parents_own_step_not_confirmed(self) -> None:
        fake_take_payment_relay = FakeTakePaymentRelay()
        pay_for_order_response = asyncio.run(
            orchestrators.PurchaseOrchestrator(
                fake_take_payment_relay, FakeStartedConfirmOrderRelay()
            ).pay_for_order(pay_for_order_request())
        )
        assert (
            pay_for_order_response.outcome is relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED
        )
        assert pay_for_order_response.reasons == ("the order was already started",)
        assert fake_take_payment_relay.taken == []

    def test_a_declined_payment_is_the_parents_payment_declined(self) -> None:
        pay_for_order_response = asyncio.run(
            orchestrators.PurchaseOrchestrator(
                FakeDecliningTakePaymentRelay(), FakeConfirmOrderRelay()
            ).pay_for_order(pay_for_order_request())
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAYMENT_DECLINED
        assert pay_for_order_response.purchases == ()
        assert pay_for_order_response.reasons == ("the processor declined the charge",)

    def test_a_child_that_answered_for_another_order_is_a_fault_before_any_payment(
        self,
    ) -> None:
        fake_take_payment_relay = FakeTakePaymentRelay()
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.PurchaseOrchestrator(
                    fake_take_payment_relay,
                    FakeConfirmOrderRelay(order_confirmed="other"),
                ).pay_for_order(pay_for_order_request())
            )
        assert "pricing of order 'other'" in excinfo.value.message
        assert fake_take_payment_relay.taken == []

    def test_a_receipt_for_another_order_is_a_fault(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.PurchaseOrchestrator(
                    FakeTakePaymentRelay(order_charged="other"),
                    FakeConfirmOrderRelay(),
                ).pay_for_order(pay_for_order_request())
            )
        assert "does not settle order o1" in excinfo.value.message
