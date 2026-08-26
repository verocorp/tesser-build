from __future__ import annotations

import tesser.testing as ts

import alpha.component.config as alpha_config
import app.config as config
import app.loader as loader
import app.repository as repository
import beta.component.config as beta_config


@ts.fake
class FakeConfigRepository(repository.ConfigRepository):

    def get(self) -> config.Config:
        spec = config.Spec(alpha_config.Config(alpha_config.Spec("memory")), beta_config.Config(beta_config.Spec("k")))
        return config.Config(spec)


def test_the_loader_builds_an_app_from_its_repository() -> None:
    loader.AppLoader(FakeConfigRepository()).load().close()
