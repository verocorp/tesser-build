from __future__ import annotations  # tesser:debt TB070

import asyncio
import typing

import tesser.testing as ts
import pytest
import restate

import ordering.adapters.runners as runners
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
class FakeRestateWorkflowContext:  # tesser:debt TB072

    def __init__(self, refusal: str = "", status_code: int = 404) -> None:
        self._refusal = refusal
        self._status_code = status_code
        self.called: list[tuple[object, str, object]] = []
        self.sent: list[tuple[object, str, object]] = []

    async def workflow_call(self, tpe: object, key: str, arg: object) -> object:
        self.called.append((tpe, key, arg))
        if self._refusal:
            raise restate.TerminalError(self._refusal, status_code=self._status_code)
        return relays.OrderOrchestratorResponse(order_id=key, total_cents=500)

    def workflow_send(self, tpe: object, key: str, arg: object) -> None:
        self.sent.append((tpe, key, arg))


@ts.helper
def order_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.OrderOrchestratorRequest:
    return relays.OrderOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestRestateOrderOrchestratorChildRunner:

    def test_running_journals_a_call_to_the_order_workflow_keyed_by_the_orders_id(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        order_orchestrator_response = asyncio.run(
            runners.RestateOrderOrchestratorChildRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                restate_order_runtime,
            ).run_order_orchestrator(order_orchestrator_request(order_id="o5"))
        )
        assert order_orchestrator_response == relays.OrderOrchestratorResponse(
            order_id="o5", total_cents=500
        )
        assert [(t, k) for t, k, _ in fake_restate_workflow_context.called] == [
            (restate_order_runtime.order_orchestrator_handler, "o5")
        ]
        assert fake_restate_workflow_context.sent == []

    def test_the_key_is_the_id_as_it_is_because_no_path_is_formed_inside_the_engine(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        asyncio.run(
            runners.RestateOrderOrchestratorChildRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).run_order_orchestrator(order_orchestrator_request(order_id="../admin?x=1#f"))
        )
        assert [k for _, k, _ in fake_restate_workflow_context.called] == ["../admin?x=1#f"]

    def test_starting_journals_a_send_and_answers_the_orders_id_at_once(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        start_order_orchestrator_response = asyncio.run(
            runners.RestateOrderOrchestratorChildRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                restate_order_runtime,
            ).start_order_orchestrator(order_orchestrator_request(order_id="o6"))
        )
        assert start_order_orchestrator_response.order_id == "o6"
        assert [(t, k) for t, k, _ in fake_restate_workflow_context.sent] == [
            (restate_order_runtime.order_orchestrator_handler, "o6")
        ]
        assert fake_restate_workflow_context.called == []

    def test_each_terminal_status_of_the_child_comes_back_as_its_kind(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        for status_code, kind in (
            (404, errors.Kind.NOT_FOUND),
            (422, errors.Kind.VALIDATION),
            (409, errors.Kind.CONFLICT),
        ):
            with pytest.raises(errors.DomainError) as excinfo:
                asyncio.run(
                    runners.RestateOrderOrchestratorChildRunner(
                        typing.cast(
                            restate.WorkflowContext,
                            FakeRestateWorkflowContext(refusal="no such sku", status_code=status_code),
                        ),
                        restate_order_runtime,
                    ).run_order_orchestrator(order_orchestrator_request(sku="nothing"))
                )
            assert excinfo.value.kind is kind
            assert excinfo.value.code == "order_rejected"
            assert excinfo.value.message == "no such sku"

    def test_a_terminal_error_of_no_domain_status_stays_terminal(self) -> None:
        with pytest.raises(restate.TerminalError) as excinfo:
            asyncio.run(
                runners.RestateOrderOrchestratorChildRunner(
                    typing.cast(
                        restate.WorkflowContext,
                        FakeRestateWorkflowContext(refusal="cancelled", status_code=500),
                    ),
                    runtimes.RestateOrderRuntime(
                        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                    ),
                ).run_order_orchestrator(order_orchestrator_request())
            )
        assert excinfo.value.status_code == 500
