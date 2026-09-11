from __future__ import annotations

import typing

import tesser.app as ts

import repo.component as repo_component


class Spec(ts.Spec):

    def __init__(self, repo: repo_component.Config) -> None:
        self.repo = repo


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.repo = spec.repo


class LayoutApp(ts.App):

    def __init__(self, app_config: AppConfig) -> None:
        self.repo = repo_component.Repo(app_config.repo)

    def close(self) -> None:
        self.repo.close()


class AppConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> AppConfig: ...


class EnvConfigRepository(AppConfigRepository):

    def get(self) -> AppConfig:
        return AppConfig(Spec(repo=repo_component.Config(repo_component.Spec())))


class AppLoader(ts.Loader):

    def __init__(self, app_config_repository: AppConfigRepository) -> None:
        self._app_config_repository = app_config_repository

    def load(self) -> LayoutApp:
        return LayoutApp(self._app_config_repository.get())


@ts.load
def load() -> LayoutApp:
    return AppLoader(EnvConfigRepository()).load()
