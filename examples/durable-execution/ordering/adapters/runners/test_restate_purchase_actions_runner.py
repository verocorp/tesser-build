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

    def __init__(self, refusal: str = "", status_code: int = 409) -> None:
        self._refusal = refusal
        self._status_code = status_code
        self.called: list[tuple[object, object]] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        self.called.append((tpe, arg))
        if self._refusal:
            raise restate.TerminalError(self._refusal, status_code=self._status_code)
        return relays.TakePaymentResponse(order_id="o1", reference="pay-o1", cents=750)


class TestRestatePurchaseActionsRunner:

    def test_running_take_payment_journals_a_call_to_the_runtimes_handler(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        take_payment_request = relays.TakePaymentRequest(order_id="o1", cents=750)
        take_payment_response = asyncio.run(
            runners.RestatePurchaseActionsRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                restate_order_runtime,
            ).run_take_payment(take_payment_request)
        )
        assert take_payment_response.reference == "pay-o1"
        assert take_payment_response.cents == 750
        assert fake_restate_workflow_context.called == [
            (restate_order_runtime.take_payment_handler, take_payment_request)
        ]

    def test_each_terminal_status_comes_back_as_its_kind(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        for status_code, kind in (
            (409, errors.Kind.CONFLICT),
            (422, errors.Kind.VALIDATION),
            (404, errors.Kind.NOT_FOUND),
        ):
            with pytest.raises(errors.DomainError) as excinfo:
                asyncio.run(
                    runners.RestatePurchaseActionsRunner(
                        typing.cast(
                            restate.WorkflowContext,
                            FakeRestateWorkflowContext(refusal="refused", status_code=status_code),
                        ),
                        restate_order_runtime,
                    ).run_take_payment(relays.TakePaymentRequest(order_id="o1", cents=750))
                )
            assert excinfo.value.kind is kind
            assert excinfo.value.code == "action_rejected"
            assert excinfo.value.message == "refused"

    def test_a_terminal_error_of_no_domain_status_stays_terminal(self) -> None:
        with pytest.raises(restate.TerminalError) as excinfo:
            asyncio.run(
                runners.RestatePurchaseActionsRunner(
                    typing.cast(
                        restate.WorkflowContext,
                        FakeRestateWorkflowContext(refusal="cancelled", status_code=500),
                    ),
                    runtimes.RestateOrderRuntime(
                        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                    ),
                ).run_take_payment(relays.TakePaymentRequest(order_id="o1", cents=750))
            )
        assert excinfo.value.status_code == 500
