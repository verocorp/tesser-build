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
        self.called: list[tuple[object, object]] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        self.called.append((tpe, arg))
        if self._refusal:
            raise restate.TerminalError(self._refusal, status_code=self._status_code)
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICED,
            prices=(relays.Price(cents=250),),
            reasons=(),
        )


class TestRestateOrderActionsRunner:

    def test_running_price_product_journals_a_call_to_the_runtimes_handler(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient())
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        price_product_request = relays.PriceProductRequest(sku="widget")
        price_product_response = asyncio.run(
            runners.RestateOrderActionsRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                restate_order_runtime,
            ).run_price_product(price_product_request)
        )
        assert price_product_response.prices[0].cents == 250
        assert fake_restate_workflow_context.called == [
            (restate_order_runtime.price_product_handler, price_product_request)
        ]

    def test_a_terminal_error_from_the_call_is_a_fault_the_runner_never_reads(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient())
        for status_code in (404, 409, 422, 500):
            with pytest.raises(restate.TerminalError) as excinfo:
                asyncio.run(
                    runners.RestateOrderActionsRunner(
                        typing.cast(
                            restate.WorkflowContext,
                            FakeRestateWorkflowContext(refusal="refused", status_code=status_code),
                        ),
                        restate_order_runtime,
                    ).run_price_product(relays.PriceProductRequest(sku="widget"))
                )
            assert excinfo.value.status_code == status_code
