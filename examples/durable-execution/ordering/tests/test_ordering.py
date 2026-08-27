from __future__ import annotations

import asyncio
import json

import ordering.adapters.handlers.restate as restate_handlers
import ordering.component.component as component
import ordering.component.config as config
import protocol.durable as durable


class TestOrderingContext:

    def test_a_workflow_run_quotes_through_the_action_handler_and_totals(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        actions = restate_handlers.ActionHandler(wired.actions)
        workflow = restate_handlers.WorkflowHandler(wired.orchestrator)
        routed: list[tuple[str, str]] = []

        async def call(service: str, handler: str, arg: bytes) -> bytes:
            routed.append((service, handler))
            return actions.quote(durable.ActionRequest(body=arg)).body

        async def run() -> durable.WorkflowResponse:
            wired.quotes.bind(call)
            return await workflow.run(
                durable.WorkflowRequest(key="o1", body=b'{"sku": "gadget", "quantity": 2}')
            )

        response = asyncio.run(run())

        assert json.loads(response.body) == {"order_id": "o1", "total_cents": 2000}
        assert routed == [("OrderingActions", "quote")]
