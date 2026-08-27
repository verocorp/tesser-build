from __future__ import annotations

import asyncio
import collections.abc as abc

import app.app as app
import app.config as config
import ordering.client.client as ordering_client
import ordering.component.config as ordering_config


class TestWiredApp:

    def test_a_real_workflow_prices_from_the_real_catalog(self) -> None:
        spec = config.Spec(ordering_config.Config(ordering_config.Spec("http://localhost:8080")))
        built = app.App(config.Config(spec))

        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            return await action()

        ran = asyncio.run(built.ordering.workflow(run).run(ordering_client.RunRequest(order_id="o1", sku="widget", quantity=2)))
        assert ran.total_cents == 500
