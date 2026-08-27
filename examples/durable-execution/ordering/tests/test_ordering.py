from __future__ import annotations

import asyncio
import collections.abc as abc
import json

import ordering.adapters.handlers.restate as restate_handlers
import ordering.component.component as component
import ordering.component.config as config
import protocol.durable as durable


class TestOrderingContext:

    def test_a_workflow_run_journals_the_price_step_and_totals(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        journal: dict[str, bytes] = {}

        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            if name not in journal:
                journal[name] = await action()
            return journal[name]

        async def invoke() -> durable.WorkflowResponse:
            handler = restate_handlers.WorkflowHandler(wired.workflow(run))
            return await handler.run(durable.WorkflowRequest(key="o1", body=b'{"sku": "gadget", "quantity": 2}'))

        first = asyncio.run(invoke())
        replayed = asyncio.run(invoke())

        assert json.loads(first.body) == {"order_id": "o1", "total_cents": 2000}
        assert replayed == first
        assert list(journal) == ["price"]
