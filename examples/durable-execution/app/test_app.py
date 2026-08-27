from __future__ import annotations

import asyncio
import collections.abc as abc

import app.app as app
import app.config as config
import ordering.client.client as ordering_client
import ordering.component.config as ordering_config


class TestApp:

    def test_the_app_wires_ordering(self) -> None:
        spec = config.Spec(ordering_config.Config(ordering_config.Spec("http://localhost:8080")))
        built = app.App(config.Config(spec))

        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            return await action()

        ran = asyncio.run(built.ordering.workflow(run).run(ordering_client.RunRequest(order_id="o1", sku="widget", quantity=1)))
        assert ran.total_cents == 250
