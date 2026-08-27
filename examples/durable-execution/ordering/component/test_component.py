from __future__ import annotations

import asyncio
import collections.abc as abc

import ordering.client.client as client
import ordering.component.component as component
import ordering.component.config as config


class TestOrdering:

    def test_an_invocation_scoped_workflow_prices_from_the_catalog(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))

        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            return await action()

        ran = asyncio.run(wired.workflow(run).run(client.RunRequest(order_id="o1", sku="widget", quantity=2)))
        assert ran.total_cents == 500
