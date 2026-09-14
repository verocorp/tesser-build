from __future__ import annotations

import asyncio
import typing

import tesser.testing as ts
import pytest
import restate

import ordering.adapters.runtimes as runtimes
import ordering.application.client as client
import ordering.application.relays as relays
import ordering.domain as domain


@ts.fake
class FakeOrderingApplicationClient(client.OrderingApplicationClient):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICED,
            prices=(relays.Price(cents=250),),
            reasons=(),
        )


@ts.fake
class FakePurchaseApplicationClient(client.PurchaseApplicationClient):

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.TAKEN,
            order_id=take_payment_request.order_id,
            payments=(
                relays.Payment(
                    reference=f"pay-{take_payment_request.order_id}",
                    cents=take_payment_request.cents,
                ),
            ),
            reasons=(),
        )


@ts.fake
class FakeUnpricedOrderingApplicationClient(client.OrderingApplicationClient):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICE_NOT_FOUND,
            prices=(),
            reasons=(f"no price for sku {price_product_request.sku!r}",),
        )


@ts.fake
class FakeDecliningPurchaseApplicationClient(client.PurchaseApplicationClient):

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.DECLINED,
            order_id=take_payment_request.order_id,
            payments=(),
            reasons=("the processor declined the charge",),
        )


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072

    def __init__(self, declining: bool = False, unpriced: bool = False) -> None:
        self._declining = declining
        self._unpriced = unpriced
        self.child_keys: list[str] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        if isinstance(arg, relays.TakePaymentRequest):
            if self._declining:
                return FakeDecliningPurchaseApplicationClient().take_payment(arg)
            return FakePurchaseApplicationClient().take_payment(arg)
        assert isinstance(arg, relays.PriceProductRequest)
        if self._unpriced:
            return FakeUnpricedOrderingApplicationClient().price_product(arg)
        return FakeOrderingApplicationClient().price_product(arg)

    async def workflow_call(self, tpe: object, key: str, arg: object) -> object:
        self.child_keys.append(key)
        if self._unpriced:
            return relays.ConfirmOrderResponse(
                outcome=relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND,
                order_id=key,
                confirmed_orders=(),
                reasons=("no price for sku 'nope'",),
            )
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id=key,
            confirmed_orders=(relays.ConfirmedOrder(total_cents=500),),
            reasons=(),
        )


@ts.helper
def confirm_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.ConfirmOrderRequest:
    return relays.ConfirmOrderRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


@ts.helper
def pay_for_order_request(
    order_id: str = "o1",
    sku: str = "widget",
    quantity: int = 2,
    payment_method: str = "card-4242",
) -> relays.PayForOrderRequest:
    return relays.PayForOrderRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity)),
        payment_method=domain.PaymentMethod(payment_method),
    )


@ts.helper
def take_payment_request(
    order_id: str = "o1", cents: int = 750, payment_method: str = "card-4242"
) -> relays.TakePaymentRequest:
    return relays.TakePaymentRequest(
        order_id=order_id, cents=cents, payment_method=payment_method
    )


@ts.helper
def restate_order_runtime() -> runtimes.RestateOrderRuntime:  # tesser:debt TB073
    return runtimes.RestateOrderRuntime(
        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
    )


class TestRestateOrderRuntime:

    def test_it_registers_two_actions_services_and_two_orchestrator_workflows(self) -> None:
        assert (
            restate_order_runtime().order_actions_service.name,
            sorted(restate_order_runtime().order_actions_service.handlers),
        ) == ("OrderActions", ["price_product"])
        assert (
            restate_order_runtime().order_orchestrator_workflow.name,
            sorted(restate_order_runtime().order_orchestrator_workflow.handlers),
        ) == ("OrderOrchestrator", ["confirm_order"])
        assert (
            restate_order_runtime().purchase_actions_service.name,
            sorted(restate_order_runtime().purchase_actions_service.handlers),
        ) == ("PurchaseActions", ["take_payment"])
        assert (
            restate_order_runtime().purchase_orchestrator_workflow.name,
            sorted(restate_order_runtime().purchase_orchestrator_workflow.handlers),
        ) == ("PurchaseOrchestrator", ["pay_for_order"])

    def test_every_registration_declares_a_bounded_retry_policy(self) -> None:
        for registered in (
            restate_order_runtime().order_actions_service,
            restate_order_runtime().order_orchestrator_workflow,
            restate_order_runtime().purchase_actions_service,
            restate_order_runtime().purchase_orchestrator_workflow,
        ):
            policy = registered.invocation_retry_policy
            assert policy is not None
            assert policy.max_attempts == 5
            assert policy.on_max_attempts == "pause"

    def test_the_take_payment_handler_hands_the_request_to_the_purchase_client(self) -> None:
        take_payment_response = asyncio.run(
            restate_order_runtime().take_payment_handler(
                typing.cast(restate.Context, None), take_payment_request()
            )
        )
        assert take_payment_response.outcome is relays.TakePaymentOutcome.TAKEN
        assert take_payment_response.payments[0].reference == "pay-o1"
        assert take_payment_response.payments[0].cents == 750

    def test_a_declined_charge_ends_the_action_as_an_outcome_not_an_error(self) -> None:
        take_payment_response = asyncio.run(
            runtimes.RestateOrderRuntime(
                FakeOrderingApplicationClient(), FakeDecliningPurchaseApplicationClient()
            ).take_payment_handler(typing.cast(restate.Context, None), take_payment_request())
        )
        assert take_payment_response.outcome is relays.TakePaymentOutcome.DECLINED
        assert take_payment_response.payments == ()

    def test_the_pay_for_order_handler_confirms_the_order_as_a_child_of_this_invocation(
        self,
    ) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        pay_for_order_response = asyncio.run(
            restate_order_runtime().pay_for_order_handler(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                pay_for_order_request(order_id="o9"),
            )
        )
        assert fake_restate_workflow_context.child_keys == ["o9"]
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAID
        assert pay_for_order_response.order_id == "o9"
        assert pay_for_order_response.purchases[0].total_cents == 500
        assert pay_for_order_response.purchases[0].payment_reference == "pay-o9"

    def test_an_unconfirmed_child_order_ends_the_purchase_as_that_outcome(self) -> None:
        pay_for_order_response = asyncio.run(
            restate_order_runtime().pay_for_order_handler(
                typing.cast(
                    restate.WorkflowContext, FakeRestateWorkflowContext(unpriced=True)
                ),
                pay_for_order_request(),
            )
        )
        assert (
            pay_for_order_response.outcome is relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED
        )
        assert pay_for_order_response.reasons == ("no price for sku 'nope'",)

    def test_a_declined_payment_ends_the_purchase_as_that_outcome(self) -> None:
        pay_for_order_response = asyncio.run(
            restate_order_runtime().pay_for_order_handler(
                typing.cast(
                    restate.WorkflowContext, FakeRestateWorkflowContext(declining=True)
                ),
                pay_for_order_request(),
            )
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAYMENT_DECLINED
        assert pay_for_order_response.reasons == ("the processor declined the charge",)

    def test_the_price_product_handler_hands_the_request_to_the_application_client(self) -> None:
        price_product_response = asyncio.run(
            restate_order_runtime().price_product_handler(
                typing.cast(restate.Context, None), relays.PriceProductRequest(sku="gadget")
            )
        )
        assert price_product_response.prices[0].cents == 250

    def test_an_unknown_sku_ends_the_action_as_an_outcome_not_an_error(self) -> None:
        price_product_response = asyncio.run(
            runtimes.RestateOrderRuntime(
                FakeUnpricedOrderingApplicationClient(), FakePurchaseApplicationClient()
            ).price_product_handler(
                typing.cast(restate.Context, None), relays.PriceProductRequest(sku="nothing")
            )
        )
        assert price_product_response.outcome is relays.PriceProductOutcome.PRICE_NOT_FOUND
        assert price_product_response.reasons == ("no price for sku 'nothing'",)

    def test_the_confirm_order_handler_runs_the_orchestrator_over_this_invocation(self) -> None:
        confirm_order_response = asyncio.run(
            restate_order_runtime().confirm_order_handler(
                typing.cast(restate.WorkflowContext, FakeRestateWorkflowContext()),
                confirm_order_request(quantity=3),
            )
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert confirm_order_response.order_id == "o1"
        assert confirm_order_response.confirmed_orders[0].total_cents == 750

    def test_an_unpriced_action_ends_the_workflow_as_that_outcome(self) -> None:
        confirm_order_response = asyncio.run(
            restate_order_runtime().confirm_order_handler(
                typing.cast(
                    restate.WorkflowContext, FakeRestateWorkflowContext(unpriced=True)
                ),
                confirm_order_request(sku="nothing"),
            )
        )
        assert (
            confirm_order_response.outcome
            is relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND
        )
        assert confirm_order_response.reasons == ("no price for sku 'nothing'",)


class TestRestateSerdes:

    def test_each_shim_writes_what_its_relay_snapshot_writes_and_reads_it_back(self) -> None:
        price_product_request = relays.PriceProductRequest(sku="widget")
        price_product_response = relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICED,
            prices=(relays.Price(cents=250),),
            reasons=(),
        )
        confirm_order_response = relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id="o1",
            confirmed_orders=(relays.ConfirmedOrder(total_cents=500),),
            reasons=(),
        )
        restate_price_product_request_serde = runtimes.RestatePriceProductRequestSerde()
        restate_price_product_response_serde = runtimes.RestatePriceProductResponseSerde()
        restate_confirm_order_response_serde = runtimes.RestateConfirmOrderResponseSerde()
        assert runtimes.RestateConfirmOrderRequestSerde().serialize(
            confirm_order_request()
        ) == relays.ConfirmOrderRequestSnapshot().serialize(confirm_order_request())
        assert restate_confirm_order_response_serde.serialize(
            confirm_order_response
        ) == relays.ConfirmOrderResponseSnapshot().serialize(confirm_order_response)
        assert restate_price_product_request_serde.serialize(
            price_product_request
        ) == relays.PriceProductRequestSnapshot().serialize(price_product_request)
        assert restate_price_product_response_serde.serialize(
            price_product_response
        ) == relays.PriceProductResponseSnapshot().serialize(price_product_response)
        assert restate_price_product_request_serde.deserialize(
            restate_price_product_request_serde.serialize(price_product_request)
        ) == price_product_request
        assert restate_price_product_response_serde.deserialize(
            restate_price_product_response_serde.serialize(price_product_response)
        ) == price_product_response
        assert restate_confirm_order_response_serde.deserialize(
            restate_confirm_order_response_serde.serialize(confirm_order_response)
        ) == confirm_order_response

    def test_each_purchase_shim_writes_what_its_relay_snapshot_writes_and_reads_it_back(self) -> None:
        take_payment_response = relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.TAKEN,
            order_id="o1",
            payments=(relays.Payment(reference="pay-o1", cents=500),),
            reasons=(),
        )
        pay_for_order_response = relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.PAID,
            order_id="o1",
            purchases=(relays.Purchase(total_cents=500, payment_reference="pay-o1"),),
            reasons=(),
        )
        restate_pay_for_order_request_serde = runtimes.RestatePayForOrderRequestSerde()
        restate_pay_for_order_response_serde = runtimes.RestatePayForOrderResponseSerde()
        restate_take_payment_request_serde = runtimes.RestateTakePaymentRequestSerde()
        restate_take_payment_response_serde = runtimes.RestateTakePaymentResponseSerde()
        assert restate_pay_for_order_request_serde.serialize(
            pay_for_order_request()
        ) == relays.PayForOrderRequestSnapshot().serialize(pay_for_order_request())
        assert restate_pay_for_order_response_serde.serialize(
            pay_for_order_response
        ) == relays.PayForOrderResponseSnapshot().serialize(pay_for_order_response)
        assert restate_take_payment_request_serde.serialize(
            take_payment_request()
        ) == relays.TakePaymentRequestSnapshot().serialize(take_payment_request())
        assert restate_take_payment_response_serde.serialize(
            take_payment_response
        ) == relays.TakePaymentResponseSnapshot().serialize(take_payment_response)
        assert restate_pay_for_order_response_serde.deserialize(
            restate_pay_for_order_response_serde.serialize(pay_for_order_response)
        ) == pay_for_order_response
        back = restate_pay_for_order_request_serde.deserialize(
            restate_pay_for_order_request_serde.serialize(
                pay_for_order_request(order_id="o7", sku="gadget", quantity=3)
            )
        )
        assert back is not None
        assert back.order.identity == domain.OrderId("o7")
        assert back.order.sku == domain.Sku("gadget")
        assert back.order.quantity == domain.Quantity(3)
        assert restate_take_payment_request_serde.deserialize(
            restate_take_payment_request_serde.serialize(take_payment_request())
        ) == take_payment_request()
        assert restate_take_payment_response_serde.deserialize(
            restate_take_payment_response_serde.serialize(take_payment_response)
        ) == take_payment_response

    def test_no_message_writes_an_empty_body_and_an_empty_body_is_terminal_on_every_shim(
        self,
    ) -> None:
        for serde in (
            runtimes.RestateConfirmOrderRequestSerde(),
            runtimes.RestateConfirmOrderResponseSerde(),
            runtimes.RestatePriceProductRequestSerde(),
            runtimes.RestatePriceProductResponseSerde(),
            runtimes.RestatePayForOrderRequestSerde(),
            runtimes.RestatePayForOrderResponseSerde(),
            runtimes.RestateTakePaymentRequestSerde(),
            runtimes.RestateTakePaymentResponseSerde(),
        ):
            assert serde.serialize(None) == b""
            with pytest.raises(restate.TerminalError) as excinfo:
                serde.deserialize(b"")
            assert excinfo.value.status_code == 400

    def test_a_body_the_snapshot_cannot_read_is_terminal_on_every_shim(self) -> None:
        for serde in (
            runtimes.RestateConfirmOrderRequestSerde(),
            runtimes.RestateConfirmOrderResponseSerde(),
            runtimes.RestatePriceProductRequestSerde(),
            runtimes.RestatePriceProductResponseSerde(),
            runtimes.RestatePayForOrderRequestSerde(),
            runtimes.RestatePayForOrderResponseSerde(),
            runtimes.RestateTakePaymentRequestSerde(),
            runtimes.RestateTakePaymentResponseSerde(),
        ):
            with pytest.raises(restate.TerminalError) as excinfo:
                serde.deserialize(b"<html>not a message</html>")
            assert excinfo.value.status_code == 400
