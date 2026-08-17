from __future__ import annotations

import tesser.testing as ts

import app.config as config
import app.loader as loader
import app.repository as repository
import tessercheck.component.config as component_config


@ts.fake
class FakeConfigRepository(repository.ConfigRepository):

    def __init__(self) -> None:
        self.reads = 0

    def get(self) -> config.Config:
        self.reads += 1
        return config.Config(
            config.Spec(tessercheck=component_config.Config(component_config.Spec()))
        )


def test_a_loader_reads_its_repository_once_per_load() -> None:
    configs = FakeConfigRepository()

    loader.AppLoader(configs).load()

    assert configs.reads == 1


def test_a_loader_returns_an_app_built_from_what_the_repository_gave_it() -> None:
    assert loader.AppLoader(FakeConfigRepository()).load().tessercheck.client is not None
