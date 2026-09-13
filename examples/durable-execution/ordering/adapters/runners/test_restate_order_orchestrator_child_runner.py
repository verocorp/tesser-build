from __future__ import annotations

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
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id=key,
            confirmed_orders=(relays.ConfirmedOrder(total_cents=500),),
            reasons=(),
        )

    def workflow_send(self, tpe: object, key: str, arg: object) -> None:
        self.sent.append((tpe, key, arg))


@ts.helper
def confirm_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.ConfirmOrderRequest:
    return relays.ConfirmOrderRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestRestateOrderOrchestratorChildRunner:

    def test_running_journals_a_call_to_the_order_workflow_keyed_by_the_orders_id(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        confirm_order_response = asyncio.run(
            runners.RestateOrderOrchestratorChildRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                restate_order_runtime,
            ).run_confirm_order(confirm_order_request(order_id="o5"))
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert confirm_order_response.order_id == "o5"
        assert confirm_order_response.confirmed_orders[0].total_cents == 500
        assert [(t, k) for t, k, _ in fake_restate_workflow_context.called] == [
            (restate_order_runtime.confirm_order_handler, "o5")
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
            ).run_confirm_order(confirm_order_request(order_id="../admin?x=1#f"))
        )
        assert [k for _, k, _ in fake_restate_workflow_context.called] == ["../admin?x=1#f"]

    def test_starting_journals_a_send_and_answers_the_orders_id_at_once(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        start_confirm_order_response = asyncio.run(
            runners.RestateOrderOrchestratorChildRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                restate_order_runtime,
            ).start_confirm_order(confirm_order_request(order_id="o6"))
        )
        assert (
            start_confirm_order_response.outcome is relays.StartConfirmOrderOutcome.STARTED
        )
        assert start_confirm_order_response.order_id == "o6"
        assert [(t, k) for t, k, _ in fake_restate_workflow_context.sent] == [
            (restate_order_runtime.confirm_order_handler, "o6")
        ]
        assert fake_restate_workflow_context.called == []

    def test_the_already_invoked_conflict_is_the_outcome_the_engine_crossing_adds(self) -> None:
        confirm_order_response = asyncio.run(
            runners.RestateOrderOrchestratorChildRunner(
                typing.cast(
                    restate.WorkflowContext,
                    FakeRestateWorkflowContext(
                        refusal="the workflow method was already invoked", status_code=409
                    ),
                ),
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).run_confirm_order(confirm_order_request(order_id="o5"))
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.ALREADY_STARTED
        assert confirm_order_response.order_id == "o5"
        assert confirm_order_response.confirmed_orders == ()
        assert confirm_order_response.reasons == ("the workflow method was already invoked",)

    def test_any_other_terminal_error_is_a_fault_the_cancellation_409_included(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        for refusal, status_code in (
            ("cancelled", 409),
            ("no such sku", 404),
            ("an order is for at least one unit", 422),
            ("Unable to parse an input argument", 500),
        ):
            with pytest.raises(restate.TerminalError) as excinfo:
                asyncio.run(
                    runners.RestateOrderOrchestratorChildRunner(
                        typing.cast(
                            restate.WorkflowContext,
                            FakeRestateWorkflowContext(
                                refusal=refusal, status_code=status_code
                            ),
                        ),
                        restate_order_runtime,
                    ).run_confirm_order(confirm_order_request())
                )
            assert excinfo.value.status_code == status_code
