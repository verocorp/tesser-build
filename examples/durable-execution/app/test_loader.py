from __future__ import annotations

import asyncio
import collections.abc as abc

import tesser.testing as ts

import app.config as config
import app.config_repository as config_repository
import app.loader as loader
import ordering.client.client as ordering_client
import ordering.component.config as ordering_config


@ts.fake
class FakeConfigRepository(config_repository.ConfigRepository):

    def get(self) -> config.Config:
        spec = config.Spec(ordering_config.Config(ordering_config.Spec("http://localhost:8080")))
        return config.Config(spec)


class TestAppLoader:

    def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        built = loader.AppLoader(FakeConfigRepository()).load()

        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            return await action()

        ran = asyncio.run(built.ordering.workflow(run).run(ordering_client.RunRequest(order_id="o1", sku="gadget", quantity=1)))
        assert ran.total_cents == 1000
