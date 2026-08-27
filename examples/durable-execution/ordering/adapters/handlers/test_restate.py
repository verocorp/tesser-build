from __future__ import annotations

import asyncio
import json

import pytest
import tesser.testing as ts

import ordering.adapters.handlers.restate as restate_handlers
import ordering.client.client as client
import protocol.durable as durable


@ts.fake
class FakeOrchestrator(client.Orchestrator):

    def __init__(self) -> None:
        self.ran: list[client.RunRequest] = []

    async def run(self, request: client.RunRequest) -> client.RunResponse:
        self.ran.append(request)
        return client.RunResponse(order_id=request.order_id, total_cents=750)


@ts.fake
class FakeActions(client.Actions):

    def quote(self, request: client.QuoteRequest) -> client.QuoteResponse:
        return client.QuoteResponse(cents=250)


class TestWorkflowHandler:

    def test_running_answers_the_total_for_the_keyed_order(self) -> None:
        handler = restate_handlers.WorkflowHandler(FakeOrchestrator())
        request = durable.WorkflowRequest(key="o1", body=b'{"sku": "widget", "quantity": 3}')
        response = asyncio.run(handler.run(request))
        assert json.loads(response.body) == {"order_id": "o1", "total_cents": 750}

    def test_the_workflow_key_is_the_order_id(self) -> None:
        fake = FakeOrchestrator()
        request = durable.WorkflowRequest(key="o9", body=b'{"sku": "widget", "quantity": 3}')
        asyncio.run(restate_handlers.WorkflowHandler(fake).run(request))
        assert [(r.order_id, r.sku, r.quantity) for r in fake.ran] == [("o9", "widget", 3)]

    def test_a_body_without_a_sku_is_a_bad_invocation(self) -> None:
        handler = restate_handlers.WorkflowHandler(FakeOrchestrator())
        with pytest.raises(durable.BadInvocation):
            asyncio.run(handler.run(durable.WorkflowRequest(key="o1", body=b'{"quantity": 3}')))


class TestActionHandler:

    def test_quoting_answers_the_cents(self) -> None:
        handler = restate_handlers.ActionHandler(FakeActions())
        response = handler.quote(durable.ActionRequest(body=b'{"sku": "widget"}'))
        assert json.loads(response.body) == {"cents": 250}
