from __future__ import annotations

import typing

import tesser.app as ts

import tessercheck.component as tessercheck_component


class Spec(ts.Spec):

    def __init__(self, tessercheck: tessercheck_component.Config) -> None:
        self.tessercheck = tessercheck


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.tessercheck = spec.tessercheck


class TessercheckApp(ts.App):

    def __init__(self, app_config: AppConfig) -> None:
        self.tessercheck = tessercheck_component.Tessercheck(app_config.tessercheck)

    def close(self) -> None:
        self.tessercheck.close()


class ConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> AppConfig: ...


class EnvConfigRepository(ConfigRepository):

    def get(self) -> AppConfig:
        return AppConfig(
            Spec(
                tessercheck=tessercheck_component.Config(tessercheck_component.Spec()),
            )
        )


class AppLoader(ts.Loader):

    def __init__(self, config_repository: ConfigRepository) -> None:
        self._config_repository = config_repository

    def load(self) -> TessercheckApp:
        return TessercheckApp(self._config_repository.get())


@ts.load
def load() -> TessercheckApp:
    return AppLoader(EnvConfigRepository()).load()
