from __future__ import annotations

import tesser.testing as ts

import alpha.client as client
import alpha.component as alpha_component
import app.config as config
import app.config_repository as config_repository
import app.loader as loader
import beta.component as beta_component


@ts.fake
class FakeConfigRepository(config_repository.AppConfigRepository):

    def get(self) -> config.AppConfig:
        spec = config.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        return config.AppConfig(spec)


class TestAppLoader:

    def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        built = loader.AppLoader(FakeConfigRepository()).load()
        added = built.alpha.client.add(client.AddRequest(name="a", part="p"))
        assert added.name == "a"
