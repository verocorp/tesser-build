from __future__ import annotations

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
        assert built.ordering.actions.quote(ordering_client.QuoteRequest(sku="gadget")).cents == 1000
