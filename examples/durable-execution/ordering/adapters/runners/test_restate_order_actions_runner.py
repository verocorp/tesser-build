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

    def prepare_quote(
        self, prepare_quote_request: relays.PrepareQuoteRequest
    ) -> relays.PrepareQuoteResponse:
        return relays.PrepareQuoteResponse(cents=250)


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072

    def __init__(self, refusal: str = "") -> None:
        self._refusal = refusal
        self.called: list[tuple[object, object]] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        self.called.append((tpe, arg))
        if self._refusal:
            raise restate.TerminalError(self._refusal, status_code=404)
        return relays.PrepareQuoteResponse(cents=250)


class TestRestateOrderActionsRunner:

    def test_running_prepare_quote_journals_a_call_to_the_runtimes_handler(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(FakeOrderingApplicationClient())
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        prepare_quote_request = relays.PrepareQuoteRequest(sku="widget")
        prepare_quote_response = asyncio.run(
            runners.RestateOrderActionsRunner(
                typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
                restate_order_runtime,
            ).run_prepare_quote(prepare_quote_request)
        )
        assert prepare_quote_response.cents == 250
        assert fake_restate_workflow_context.called == [
            (restate_order_runtime.prepare_quote_handler, prepare_quote_request)
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
                ).run_prepare_quote(relays.PrepareQuoteRequest(sku="nothing"))
            )
        assert excinfo.value.kind is errors.Kind.NOT_FOUND
        assert excinfo.value.code == "action_rejected"
        assert excinfo.value.message == "no such sku"
