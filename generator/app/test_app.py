from __future__ import annotations

import pathlib

import tesser.testing as ts

import app
import trees.component as trees_component


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def __init__(self) -> None:
        self.reads = 0

    def get(self) -> app.AppConfig:
        self.reads += 1
        return app.AppConfig(app.Spec(trees=trees_component.Config(trees_component.Spec(templates_root="/templates"))))


class TestAppConfig:

    def test_a_config_carries_the_trees_config(self) -> None:
        config = trees_component.Config(trees_component.Spec(templates_root="/templates"))

        assert app.AppConfig(app.Spec(trees=config)).trees is config


class TestEnvConfigRepository:

    def test_the_templates_root_is_the_templates_directory_beside_the_app(self) -> None:
        app_config = app.EnvConfigRepository().get()

        assert pathlib.Path(app_config.trees.templates_root).is_dir()
        assert pathlib.Path(app_config.trees.templates_root).name == "templates"


class TestAppLoader:

    def test_a_loader_reads_its_repository_once_per_load(self) -> None:
        fake_config_repository = FakeConfigRepository()

        app.AppLoader(fake_config_repository).load().close()

        assert fake_config_repository.reads == 1

    def test_a_loaded_app_publishes_the_trees_client(self) -> None:
        generator_app = app.AppLoader(FakeConfigRepository()).load()

        assert generator_app.trees.client is not None
        generator_app.close()
