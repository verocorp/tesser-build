from __future__ import annotations

import tesser.testing as ts
from tesser.app import ConfigRepository

import bootstrap.config as config
import bootstrap.loader as loader
import repo.wiring.config as repo_config


@ts.fake
class FakeConfigRepository(ConfigRepository[config.Config]):

    def __init__(self) -> None:
        self.reads = 0

    def get(self) -> config.Config:
        self.reads += 1
        return config.Config(config.Spec(repo=repo_config.Config(repo_config.Spec())))


def test_a_loader_reads_its_repository_once_per_load() -> None:
    configs = FakeConfigRepository()

    loader.AppLoader(configs).load()

    assert configs.reads == 1


def test_a_loader_returns_an_app_built_from_what_the_repository_gave_it() -> None:
    assert loader.AppLoader(FakeConfigRepository()).load().repo.client is not None
