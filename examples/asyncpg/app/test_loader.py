from __future__ import annotations

import os

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
        alpha_storage = os.environ["ALPHA_STORAGE"]
        beta_storage = os.environ["BETA_STORAGE"]
        spec = config.Spec(
            alpha_config.Config(alpha_config.Spec(alpha_storage)),
            beta_config.Config(beta_config.Spec(beta_storage)),
        )
        return config.Config(spec)


class TestAppLoader:

    async def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        app = loader.AppLoader(FakeConfigRepository()).load()
        await app.open()
        added = await app.alpha.client.add(alpha_client.AddRequest(name="loader-a", part="p"))
        await app.close()
        assert added.name == "loader-a"
