from __future__ import annotations

import tesser.testing as ts

import alpha.client.client as alpha_client
import alpha.component.config as alpha_config
import app.config as config
import app.config_repository as config_repository
import app.loader as loader
import beta.component.config as beta_config


@ts.fake
class FakeConfigRepository(config_repository.ConfigRepository):

    def get(self) -> config.Config:
        spec = config.Spec(alpha_config.Config(alpha_config.Spec("memory")), beta_config.Config(beta_config.Spec("memory")))
        return config.Config(spec)


class TestAppLoader:

    async def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        built = loader.AppLoader(FakeConfigRepository()).load()
        await built.start()
        added = await built.alpha.client.add(alpha_client.AddRequest(name="a", part="p"))
        await built.close()
        assert added.name == "a"
