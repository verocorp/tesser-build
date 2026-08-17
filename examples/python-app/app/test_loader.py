from __future__ import annotations

import tesser.testing as ts

import app.config as config
import app.loader as loader
import app.repository as repository
import campaign.component.config as campaign_config
import linkpolicy.component.config as linkpolicy_config
import reports.component.config as reports_config


@ts.fake
class FakeConfigRepository(repository.ConfigRepository):

    def __init__(self) -> None:
        self.reads = 0

    def get(self) -> config.Config:
        self.reads += 1
        return config.Config(
            config.Spec(
                campaign=campaign_config.Config(campaign_config.Spec(storage="memory")),
                linkpolicy=linkpolicy_config.Config(linkpolicy_config.Spec(storage="memory")),
                reports=reports_config.Config(reports_config.Spec()),
                http=config.HttpConfig(config.HttpSpec("", 8080)),
            )
        )


def test_a_loader_reads_its_repository_once_per_load() -> None:
    configs = FakeConfigRepository()

    loader.AppLoader(configs).load()

    assert configs.reads == 1


def test_a_loader_returns_an_app_built_from_what_the_repository_gave_it() -> None:
    built = loader.AppLoader(FakeConfigRepository()).load()

    assert built.http.port == 8080
    built.close()


def test_each_load_builds_its_own_app() -> None:
    configs = FakeConfigRepository()

    first = loader.AppLoader(configs).load()
    second = loader.AppLoader(configs).load()

    assert first.campaign.client is not second.campaign.client
    first.close()
    second.close()
