from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import restate.client

import ordering.adapters.gateways.restate_workflow as restate_workflow
import ordering.application.ports.order_workflow as order_workflow
import tesser.errors as errors


class TestRestateOrderWorkflow:

    def test_starting_sends_the_order_to_the_workflow_keyed_by_its_id(self) -> None:
        seen: list[httpx.Request] = []

        def ingress(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(202, json={"invocationId": "inv_1", "status": "Accepted"})

        async def start() -> order_workflow.StartResponse:
            async with httpx.AsyncClient(base_url="http://ingress", transport=httpx.MockTransport(ingress)) as http:
                workflows = restate_workflow.RestateOrderWorkflow(restate.client.Client(http), "Ordering", "run")
                return await workflows.start(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))

        started = asyncio.run(start())

        assert started.order_id == "o1"
        assert seen[0].url.path == "/Ordering/o1/run/send"
        assert seen[0].headers["content-type"] == "application/json"
        assert json.loads(seen[0].content) == {"sku": "widget", "quantity": 2}

    def test_a_refused_send_is_an_infra_error(self) -> None:
        def ingress(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="Not Found")

        async def start() -> order_workflow.StartResponse:
            async with httpx.AsyncClient(base_url="http://ingress", transport=httpx.MockTransport(ingress)) as http:
                workflows = restate_workflow.RestateOrderWorkflow(restate.client.Client(http), "Ordering", "run")
                return await workflows.start(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))

        with pytest.raises(errors.InfraError):
            asyncio.run(start())

    def test_an_unreachable_ingress_is_an_infra_error(self) -> None:
        def ingress(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        async def start() -> order_workflow.StartResponse:
            async with httpx.AsyncClient(base_url="http://ingress", transport=httpx.MockTransport(ingress)) as http:
                workflows = restate_workflow.RestateOrderWorkflow(restate.client.Client(http), "Ordering", "run")
                return await workflows.start(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))

        with pytest.raises(errors.InfraError):
            asyncio.run(start())
