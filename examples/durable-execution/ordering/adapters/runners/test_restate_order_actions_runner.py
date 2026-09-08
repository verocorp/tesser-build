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
class FakeRestateWorkflowContext:  # tesser:debt TB072

    def __init__(self, refusal: str = "", status_code: int = 404) -> None:
        self._refusal = refusal
        self._status_code = status_code
        self.called: list[tuple[object, object]] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        self.called.append((tpe, arg))
        if self._refusal:
            raise restate.TerminalError(self._refusal, status_code=self._status_code)
        return relays.PriceProductResponse(cents=250)


class TestRestateOrderActionsRunner:

    def test_running_price_product_journals_a_call_to_the_runtimes_handler(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(FakeOrderingApplicationClient())
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        price_product_request = relays.PriceProductRequest(sku="widget")
        price_product_response = asyncio.run(
            runners.RestateOrderActionsRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                restate_order_runtime,
            ).run_price_product(price_product_request)
        )
        assert price_product_response.cents == 250
        assert fake_restate_workflow_context.called == [
            (restate_order_runtime.price_product_handler, price_product_request)
        ]

    def test_a_terminal_error_from_the_call_is_a_domain_error(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(FakeOrderingApplicationClient())
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                runners.RestateOrderActionsRunner(
                    typing.cast(
                        restate.WorkflowContext, FakeRestateWorkflowContext(refusal="no such sku")
                    ),
                    restate_order_runtime,
                ).run_price_product(relays.PriceProductRequest(sku="nothing"))
            )
        assert excinfo.value.kind is errors.Kind.NOT_FOUND
        assert excinfo.value.code == "action_rejected"
        assert excinfo.value.message == "no such sku"

    def test_each_terminal_status_comes_back_as_its_kind(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(FakeOrderingApplicationClient())
        for status_code, kind in ((422, errors.Kind.VALIDATION), (409, errors.Kind.CONFLICT)):
            with pytest.raises(errors.DomainError) as excinfo:
                asyncio.run(
                    runners.RestateOrderActionsRunner(
                        typing.cast(
                            restate.WorkflowContext,
                            FakeRestateWorkflowContext(refusal="refused", status_code=status_code),
                        ),
                        restate_order_runtime,
                    ).run_price_product(relays.PriceProductRequest(sku="widget"))
                )
            assert excinfo.value.kind is kind

    def test_a_terminal_error_of_no_domain_status_stays_terminal(self) -> None:
        with pytest.raises(restate.TerminalError) as excinfo:
            asyncio.run(
                runners.RestateOrderActionsRunner(
                    typing.cast(
                        restate.WorkflowContext,
                        FakeRestateWorkflowContext(refusal="cancelled", status_code=500),
                    ),
                    runtimes.RestateOrderRuntime(FakeOrderingApplicationClient()),
                ).run_price_product(relays.PriceProductRequest(sku="widget"))
            )
        assert excinfo.value.status_code == 500
