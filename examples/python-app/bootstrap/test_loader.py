from __future__ import annotations

import tesser.testing as ts

import bootstrap.config as config
import bootstrap.loader as loader
import campaign.wiring.config as campaign_config
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config


@ts.fake
class FakeConfigRepository:  # tessercheck:ignore TB072

    def __init__(self, campaign_storage: str) -> None:
        self.reads = 0
        self._campaign_storage = campaign_storage

    def get(self) -> config.Config:
        self.reads += 1
        return config.Config(
            campaign=campaign_config.Config(storage=self._campaign_storage),
            linkpolicy=linkpolicy_config.Config(storage="memory"),
            reports=reports_config.Config(),
            http=config.HttpConfig("", 8080),
        )


def test_a_loader_reads_its_repository_once_per_load() -> None:
    configs = FakeConfigRepository("memory")

    loader.AppLoader(configs).load()

    assert configs.reads == 1


def test_a_loader_returns_an_app_built_from_what_the_repository_gave_it() -> None:
    built = loader.AppLoader(FakeConfigRepository("memory")).load()

    assert built.http.port == 8080
    built.close()


def test_each_load_builds_its_own_app() -> None:
    configs = FakeConfigRepository("memory")

    first = loader.AppLoader(configs).load()
    second = loader.AppLoader(configs).load()

    assert first.campaign.client is not second.campaign.client
    first.close()
    second.close()
