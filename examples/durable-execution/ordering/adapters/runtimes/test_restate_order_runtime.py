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

    def prepare_quote(
        self, prepare_quote_request: relays.PrepareQuoteRequest
    ) -> relays.PrepareQuoteResponse:
        return relays.PrepareQuoteResponse(cents=250)


@ts.fake
class FakeRefusingOrderingApplicationClient(client.OrderingApplicationClient):

    def prepare_quote(
        self, prepare_quote_request: relays.PrepareQuoteRequest
    ) -> relays.PrepareQuoteResponse:
        raise errors.not_found("unknown_sku", f"no price for sku {prepare_quote_request.sku!r}")


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072

    def __init__(self, refusal: str = "") -> None:
        self._refusal = refusal

    async def service_call(self, tpe: object, arg: object) -> object:
        if self._refusal:
            raise restate.TerminalError(self._refusal, status_code=404)
        return relays.PrepareQuoteResponse(cents=250)


@ts.helper
def order_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.OrderOrchestratorRequest:
    return relays.OrderOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestRestateOrderRuntime:

    def test_it_registers_the_actions_service_and_the_orchestrator_workflow(self) -> None:
        restate_order_runtime = runtimes.RestateOrderRuntime(FakeOrderingApplicationClient())
        assert (
            restate_order_runtime.order_actions_service.name,
            sorted(restate_order_runtime.order_actions_service.handlers),
        ) == ("OrderActions", ["prepare_quote"])
        assert (
            restate_order_runtime.order_orchestrator_workflow.name,
            sorted(restate_order_runtime.order_orchestrator_workflow.handlers),
        ) == ("OrderOrchestrator", ["run"])

    def test_the_prepare_quote_handler_hands_the_request_to_the_application_client(self) -> None:
        prepare_quote_response = asyncio.run(
            runtimes.RestateOrderRuntime(FakeOrderingApplicationClient()).prepare_quote_handler(
                typing.cast(restate.Context, None), relays.PrepareQuoteRequest(sku="gadget")
            )
        )
        assert prepare_quote_response.cents == 250

    def test_a_domain_error_from_the_actions_ends_the_invocation_terminally(self) -> None:
        with pytest.raises(restate.TerminalError) as excinfo:
            asyncio.run(
                runtimes.RestateOrderRuntime(
                    FakeRefusingOrderingApplicationClient()
                ).prepare_quote_handler(
                    typing.cast(restate.Context, None), relays.PrepareQuoteRequest(sku="nothing")
                )
            )
        assert excinfo.value.status_code == 404

    def test_the_orchestrator_handler_runs_the_orchestrator_over_this_invocation(self) -> None:
        order_orchestrator_response = asyncio.run(
            runtimes.RestateOrderRuntime(FakeOrderingApplicationClient()).order_orchestrator_handler(
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
                    FakeOrderingApplicationClient()
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
        prepare_quote_request = relays.PrepareQuoteRequest(sku="widget")
        prepare_quote_response = relays.PrepareQuoteResponse(cents=250)
        order_orchestrator_response = relays.OrderOrchestratorResponse(order_id="o1", total_cents=500)
        assert runtimes.RestateOrderOrchestratorRequestSerde().serialize(
            order_orchestrator_request()
        ) == relays.OrderOrchestratorRequestSnapshot().serialize(order_orchestrator_request())
        assert runtimes.RestateOrderOrchestratorResponseSerde().serialize(
            order_orchestrator_response
        ) == relays.OrderOrchestratorResponseSnapshot().serialize(order_orchestrator_response)
        assert runtimes.RestatePrepareQuoteRequestSerde().serialize(
            prepare_quote_request
        ) == relays.PrepareQuoteRequestSnapshot().serialize(prepare_quote_request)
        assert runtimes.RestatePrepareQuoteResponseSerde().serialize(
            prepare_quote_response
        ) == relays.PrepareQuoteResponseSnapshot().serialize(prepare_quote_response)

    def test_each_shim_reads_back_what_it_wrote(self) -> None:
        prepare_quote_request = relays.PrepareQuoteRequest(sku="widget")
        prepare_quote_response = relays.PrepareQuoteResponse(cents=250)
        order_orchestrator_response = relays.OrderOrchestratorResponse(order_id="o1", total_cents=500)
        restate_prepare_quote_request_serde = runtimes.RestatePrepareQuoteRequestSerde()
        restate_prepare_quote_response_serde = runtimes.RestatePrepareQuoteResponseSerde()
        restate_order_orchestrator_response_serde = runtimes.RestateOrderOrchestratorResponseSerde()
        assert restate_prepare_quote_request_serde.deserialize(
            restate_prepare_quote_request_serde.serialize(prepare_quote_request)
        ) == prepare_quote_request
        assert restate_prepare_quote_response_serde.deserialize(
            restate_prepare_quote_response_serde.serialize(prepare_quote_response)
        ) == prepare_quote_response
        assert restate_order_orchestrator_response_serde.deserialize(
            restate_order_orchestrator_response_serde.serialize(order_orchestrator_response)
        ) == order_orchestrator_response

    def test_an_empty_body_is_no_message_on_every_shim(self) -> None:
        for serde in (
            runtimes.RestateOrderOrchestratorRequestSerde(),
            runtimes.RestateOrderOrchestratorResponseSerde(),
            runtimes.RestatePrepareQuoteRequestSerde(),
            runtimes.RestatePrepareQuoteResponseSerde(),
        ):
            assert serde.serialize(None) == b""
            assert serde.deserialize(b"") is None
