from __future__ import annotations

import tesser.testing as ts

import app
import repo.component as repo_component


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def __init__(self) -> None:
        self.reads = 0

    def get(self) -> app.AppConfig:
        self.reads += 1
        return app.AppConfig(app.Spec(repo=repo_component.Config(repo_component.Spec())))


def test_a_config_carries_the_slice_its_component_reads() -> None:
    config = repo_component.Config(repo_component.Spec())

    assert app.AppConfig(app.Spec(repo=config)).repo is config


def test_the_env_repository_reads_a_config() -> None:
    assert isinstance(app.EnvConfigRepository().get(), app.AppConfig)


def test_each_read_returns_its_own_config() -> None:
    env_config_repository = app.EnvConfigRepository()

    assert env_config_repository.get() is not env_config_repository.get()


def test_an_app_builds_one_component_per_slice() -> None:
    app_config = app.AppConfig(app.Spec(repo=repo_component.Config(repo_component.Spec())))

    assert app.LayoutApp(app_config).repo.client is not None


def test_an_app_closes_its_components() -> None:
    app_config = app.AppConfig(app.Spec(repo=repo_component.Config(repo_component.Spec())))
    layout_app = app.LayoutApp(app_config)

    layout_app.close()

    assert layout_app.repo.client is not None


def test_a_loader_reads_its_repository_once_per_load() -> None:
    fake_config_repository = FakeConfigRepository()

    app.AppLoader(fake_config_repository).load()

    assert fake_config_repository.reads == 1


def test_a_loader_returns_an_app_built_from_what_the_repository_gave_it() -> None:
    assert app.AppLoader(FakeConfigRepository()).load().repo.client is not None
