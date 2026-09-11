from __future__ import annotations

import tesser.testing as ts

import app
import tessercheck.component as tessercheck_component


@ts.fake
class FakeConfigRepository(app.ConfigRepository):

    def __init__(self) -> None:
        self.reads = 0

    def get(self) -> app.AppConfig:
        self.reads += 1
        return app.AppConfig(
            app.Spec(tessercheck=tessercheck_component.Config(tessercheck_component.Spec()))
        )


def test_a_config_carries_the_slice_its_component_reads() -> None:
    config = tessercheck_component.Config(tessercheck_component.Spec())

    app_config = app.AppConfig(app.Spec(tessercheck=config))

    assert app_config.tessercheck is config


def test_each_config_carries_its_own_slice() -> None:
    first = app.AppConfig(
        app.Spec(tessercheck=tessercheck_component.Config(tessercheck_component.Spec()))
    )
    second = app.AppConfig(
        app.Spec(tessercheck=tessercheck_component.Config(tessercheck_component.Spec()))
    )

    assert first.tessercheck is not second.tessercheck


def test_the_env_repository_reads_a_config() -> None:
    assert isinstance(app.EnvConfigRepository().get(), app.AppConfig)


def test_each_read_returns_its_own_config() -> None:
    env_config_repository = app.EnvConfigRepository()

    assert env_config_repository.get() is not env_config_repository.get()


def test_an_app_builds_one_component_per_slice() -> None:
    app_config = app.AppConfig(
        app.Spec(tessercheck=tessercheck_component.Config(tessercheck_component.Spec()))
    )

    assert app.TessercheckApp(app_config).tessercheck.client is not None


def test_an_app_closes_its_components() -> None:
    app_config = app.AppConfig(
        app.Spec(tessercheck=tessercheck_component.Config(tessercheck_component.Spec()))
    )
    tessercheck_app = app.TessercheckApp(app_config)

    tessercheck_app.close()

    assert tessercheck_app.tessercheck.client is not None


def test_a_loader_reads_its_repository_once_per_load() -> None:
    fake_config_repository = FakeConfigRepository()

    app.AppLoader(fake_config_repository).load()

    assert fake_config_repository.reads == 1


def test_a_loader_returns_an_app_built_from_what_the_repository_gave_it() -> None:
    assert app.AppLoader(FakeConfigRepository()).load().tessercheck.client is not None
