from __future__ import annotations

import json

import pytest
import restate

import ordering.adapters.gateways.restate_workflow as restate_workflow
import ordering.application.ports.order_workflow as order_workflow
import tesser.errors as errors


class TestRestateOrderWorkflow:

    def test_starting_sends_the_order_to_the_workflow_keyed_by_its_id(self) -> None:
        sent: list[tuple[str, str, bytes, str]] = []

        async def send(service: str, handler: str, arg: bytes, key: str) -> None:
            sent.append((service, handler, arg, key))

        workflows = restate_workflow.RestateOrderWorkflow(send)
        started = workflows.start(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))

        assert started.order_id == "o1"
        service, handler, arg, key = sent[0]
        assert (service, handler, key) == (restate_workflow.WORKFLOW, restate_workflow.RUN, "o1")
        assert json.loads(arg) == {"sku": "widget", "quantity": 2}

    def test_a_refused_send_is_an_infra_error(self) -> None:
        async def send(service: str, handler: str, arg: bytes, key: str) -> None:
            raise restate.HttpError(404, "Not Found")

        workflows = restate_workflow.RestateOrderWorkflow(send)
        with pytest.raises(errors.InfraError):
            workflows.start(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))
