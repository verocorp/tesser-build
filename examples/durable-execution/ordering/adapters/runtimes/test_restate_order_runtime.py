from __future__ import annotations  # tesser:debt TB070

import asyncio
import typing

import tesser.testing as ts
import pytest
import restate

import ordering.adapters.runtimes as runtimes
import ordering.application.client as client
import ordering.application.relays as relays
import ordering.domain as domain
import tesser.errors as errors


@ts.fake
class FakeOrderingApplicationClient(client.OrderingApplicationClient):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(cents=250)


@ts.fake
class FakePurchaseApplicationClient(client.PurchaseApplicationClient):

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return relays.TakePaymentResponse(
            order_id=take_payment_request.order_id,
            reference=f"pay-{take_payment_request.order_id}",
            cents=take_payment_request.cents,
        )


@ts.fake
class FakeRefusingOrderingApplicationClient(client.OrderingApplicationClient):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        raise errors.not_found("unknown_sku", f"no price for sku {price_product_request.sku!r}")


@ts.fake
class FakeRefusingPurchaseApplicationClient(client.PurchaseApplicationClient):

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        raise errors.conflict(
            "payment_already_taken", f"order {take_payment_request.order_id!r} has already been charged"
        )


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072

    def __init__(self, refusal: str = "") -> None:
        self._refusal = refusal
        self.child_keys: list[str] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        if self._refusal:
            raise restate.TerminalError(self._refusal, status_code=404)
        if isinstance(arg, relays.TakePaymentRequest):
            return relays.TakePaymentResponse(order_id=arg.order_id, reference=f"pay-{arg.order_id}", cents=arg.cents)
        return relays.PriceProductResponse(cents=250)

    async def workflow_call(self, tpe: object, key: str, arg: object) -> object:
        self.child_keys.append(key)
        if self._refusal:
            raise restate.TerminalError(self._refusal, status_code=404)
        return relays.OrderOrchestratorResponse(order_id=key, total_cents=500)


@ts.helper
def order_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.OrderOrchestratorRequest:
    return relays.OrderOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


@ts.helper
def purchase_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.PurchaseOrchestratorRequest:
    return relays.PurchaseOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestRestateOrderRuntime:

    def test_it_registers_two_actions_services_and_two_orchestrator_workflows(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient())
        assert (
            restate_order_runtime.order_actions_service.name,
            sorted(restate_order_runtime.order_actions_service.handlers),
        ) == ("OrderActions", ["price_product"])
        assert (
            restate_order_runtime.order_orchestrator_workflow.name,
            sorted(restate_order_runtime.order_orchestrator_workflow.handlers),
        ) == ("OrderOrchestrator", ["run"])
        assert (
            restate_order_runtime.purchase_actions_service.name,
            sorted(restate_order_runtime.purchase_actions_service.handlers),
        ) == ("PurchaseActions", ["take_payment"])
        assert (
            restate_order_runtime.purchase_orchestrator_workflow.name,
            sorted(restate_order_runtime.purchase_orchestrator_workflow.handlers),
        ) == ("PurchaseOrchestrator", ["run"])

    def test_the_take_payment_handler_hands_the_request_to_the_purchase_client(self) -> None:
        take_payment_response = asyncio.run(
            runtimes.RestateOrderRuntime(
                FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
            ).take_payment_handler(
                typing.cast(restate.Context, None),
                relays.TakePaymentRequest(order_id="o1", cents=750),
            )
        )
        assert take_payment_response.reference == "pay-o1"
        assert take_payment_response.cents == 750

    def test_a_domain_error_from_the_purchase_actions_ends_the_invocation_terminally(self) -> None:
        with pytest.raises(restate.TerminalError) as excinfo:
            asyncio.run(
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakeRefusingPurchaseApplicationClient()
                ).take_payment_handler(
                    typing.cast(restate.Context, None),
                    relays.TakePaymentRequest(order_id="o1", cents=750),
                )
            )
        assert excinfo.value.status_code == 409

    def test_the_purchase_handler_runs_the_order_as_a_child_over_this_invocation(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        purchase_orchestrator_response = asyncio.run(
            runtimes.RestateOrderRuntime(
                FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
            ).purchase_orchestrator_handler(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                purchase_orchestrator_request(order_id="o9"),
            )
        )
        assert fake_restate_workflow_context.child_keys == ["o9"]
        assert purchase_orchestrator_response.order_id == "o9"
        assert purchase_orchestrator_response.total_cents == 500
        assert purchase_orchestrator_response.payment_reference == "pay-o9"

    def test_a_refused_child_order_ends_the_purchase_terminally_with_its_status(self) -> None:
        with pytest.raises(restate.TerminalError) as excinfo:
            asyncio.run(
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ).purchase_orchestrator_handler(
                    typing.cast(
                        restate.WorkflowContext, FakeRestateWorkflowContext(refusal="no such sku")
                    ),
                    purchase_orchestrator_request(),
                )
            )
        assert excinfo.value.status_code == 404

    def test_the_price_product_handler_hands_the_request_to_the_application_client(self) -> None:
        price_product_response = asyncio.run(
            runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()).price_product_handler(
                typing.cast(restate.Context, None), relays.PriceProductRequest(sku="gadget")
            )
        )
        assert price_product_response.cents == 250

    def test_a_domain_error_from_the_actions_ends_the_invocation_terminally(self) -> None:
        with pytest.raises(restate.TerminalError) as excinfo:
            asyncio.run(
                runtimes.RestateOrderRuntime(
                    FakeRefusingOrderingApplicationClient(), FakePurchaseApplicationClient()
                ).price_product_handler(
                    typing.cast(restate.Context, None), relays.PriceProductRequest(sku="nothing")
                )
            )
        assert excinfo.value.status_code == 404

    def test_the_orchestrator_handler_runs_the_orchestrator_over_this_invocation(self) -> None:
        order_orchestrator_response = asyncio.run(
            runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()).order_orchestrator_handler(
                typing.cast(restate.WorkflowContext, FakeRestateWorkflowContext()),
                order_orchestrator_request(quantity=3),
            )
        )
        assert order_orchestrator_response.order_id == "o1"
        assert order_orchestrator_response.total_cents == 750

    def test_a_refused_action_ends_the_workflow_terminally_with_its_status(self) -> None:
        with pytest.raises(restate.TerminalError) as excinfo:
            asyncio.run(
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ).order_orchestrator_handler(
                    typing.cast(
                        restate.WorkflowContext, FakeRestateWorkflowContext(refusal="no such sku")
                    ),
                    order_orchestrator_request(),
                )
            )
        assert excinfo.value.status_code == 404


class TestRestateSerdes:

    def test_each_shim_writes_what_its_relay_snapshot_writes(self) -> None:
        price_product_request = relays.PriceProductRequest(sku="widget")
        price_product_response = relays.PriceProductResponse(cents=250)
        order_orchestrator_response = relays.OrderOrchestratorResponse(order_id="o1", total_cents=500)
        assert runtimes.RestateOrderOrchestratorRequestSerde().serialize(
            order_orchestrator_request()
        ) == relays.OrderOrchestratorRequestSnapshot().serialize(order_orchestrator_request())
        assert runtimes.RestateOrderOrchestratorResponseSerde().serialize(
            order_orchestrator_response
        ) == relays.OrderOrchestratorResponseSnapshot().serialize(order_orchestrator_response)
        assert runtimes.RestatePriceProductRequestSerde().serialize(
            price_product_request
        ) == relays.PriceProductRequestSnapshot().serialize(price_product_request)
        assert runtimes.RestatePriceProductResponseSerde().serialize(
            price_product_response
        ) == relays.PriceProductResponseSnapshot().serialize(price_product_response)

    def test_each_shim_reads_back_what_it_wrote(self) -> None:
        price_product_request = relays.PriceProductRequest(sku="widget")
        price_product_response = relays.PriceProductResponse(cents=250)
        order_orchestrator_response = relays.OrderOrchestratorResponse(order_id="o1", total_cents=500)
        restate_price_product_request_serde = runtimes.RestatePriceProductRequestSerde()
        restate_price_product_response_serde = runtimes.RestatePriceProductResponseSerde()
        restate_order_orchestrator_response_serde = runtimes.RestateOrderOrchestratorResponseSerde()
        assert restate_price_product_request_serde.deserialize(
            restate_price_product_request_serde.serialize(price_product_request)
        ) == price_product_request
        assert restate_price_product_response_serde.deserialize(
            restate_price_product_response_serde.serialize(price_product_response)
        ) == price_product_response
        assert restate_order_orchestrator_response_serde.deserialize(
            restate_order_orchestrator_response_serde.serialize(order_orchestrator_response)
        ) == order_orchestrator_response

    def test_each_purchase_shim_writes_what_its_relay_snapshot_writes_and_reads_it_back(self) -> None:
        take_payment_request = relays.TakePaymentRequest(order_id="o1", cents=500)
        take_payment_response = relays.TakePaymentResponse(order_id="o1", reference="pay-o1", cents=500)
        purchase_orchestrator_response = relays.PurchaseOrchestratorResponse(
            order_id="o1", total_cents=500, payment_reference="pay-o1"
        )
        restate_purchase_orchestrator_request_serde = runtimes.RestatePurchaseOrchestratorRequestSerde()
        restate_purchase_orchestrator_response_serde = runtimes.RestatePurchaseOrchestratorResponseSerde()
        restate_take_payment_request_serde = runtimes.RestateTakePaymentRequestSerde()
        restate_take_payment_response_serde = runtimes.RestateTakePaymentResponseSerde()
        assert restate_purchase_orchestrator_request_serde.serialize(
            purchase_orchestrator_request()
        ) == relays.PurchaseOrchestratorRequestSnapshot().serialize(purchase_orchestrator_request())
        assert restate_purchase_orchestrator_response_serde.serialize(
            purchase_orchestrator_response
        ) == relays.PurchaseOrchestratorResponseSnapshot().serialize(purchase_orchestrator_response)
        assert restate_take_payment_request_serde.serialize(
            take_payment_request
        ) == relays.TakePaymentRequestSnapshot().serialize(take_payment_request)
        assert restate_take_payment_response_serde.serialize(
            take_payment_response
        ) == relays.TakePaymentResponseSnapshot().serialize(take_payment_response)
        assert restate_purchase_orchestrator_response_serde.deserialize(
            restate_purchase_orchestrator_response_serde.serialize(purchase_orchestrator_response)
        ) == purchase_orchestrator_response
        back = restate_purchase_orchestrator_request_serde.deserialize(
            restate_purchase_orchestrator_request_serde.serialize(
                purchase_orchestrator_request(order_id="o7", sku="gadget", quantity=3)
            )
        )
        assert back is not None
        assert back.order.identity == domain.OrderId("o7")
        assert back.order.sku == domain.Sku("gadget")
        assert back.order.quantity == domain.Quantity(3)
        assert restate_take_payment_request_serde.deserialize(
            restate_take_payment_request_serde.serialize(take_payment_request)
        ) == take_payment_request
        assert restate_take_payment_response_serde.deserialize(
            restate_take_payment_response_serde.serialize(take_payment_response)
        ) == take_payment_response

    def test_no_message_writes_an_empty_body_and_an_empty_body_is_refused_on_every_shim(self) -> None:
        for serde in (
            runtimes.RestateOrderOrchestratorRequestSerde(),
            runtimes.RestateOrderOrchestratorResponseSerde(),
            runtimes.RestatePriceProductRequestSerde(),
            runtimes.RestatePriceProductResponseSerde(),
            runtimes.RestatePurchaseOrchestratorRequestSerde(),
            runtimes.RestatePurchaseOrchestratorResponseSerde(),
            runtimes.RestateTakePaymentRequestSerde(),
            runtimes.RestateTakePaymentResponseSerde(),
        ):
            assert serde.serialize(None) == b""
            with pytest.raises(errors.DomainError) as excinfo:
                serde.deserialize(b"")
            assert excinfo.value.kind is errors.Kind.VALIDATION
