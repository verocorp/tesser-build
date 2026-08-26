from __future__ import annotations

import os

import tesser.testing as ts

import alpha.component.config as alpha_config
import app.config as config
import app.loader as loader
import app.repository as repository
import beta.component.config as beta_config


@ts.fake
class FakeConfigRepository(repository.ConfigRepository):

    def get(self) -> config.Config:
        return config.Config(
            config.Spec(
                alpha=alpha_config.Config(alpha_config.Spec(storage="memory")),
                beta=beta_config.Config(beta_config.Spec(keys=())),
            )
        )


def test_the_loader_builds_an_app_from_its_repository() -> None:
    built = loader.AppLoader(FakeConfigRepository()).load()
    built.close()


def test_load_reads_the_environment() -> None:
    os.environ["ALPHA_STORAGE"] = "memory"
    os.environ["BETA_KEYS"] = ""
    loader.load().close()
