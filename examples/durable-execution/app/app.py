from __future__ import annotations

import os
import typing

import tesser.app as ts

import ordering.component as component
import tesser.errors as errors


class Spec(ts.Spec):

    def __init__(self, ordering: component.Config) -> None:
        self.ordering = ordering


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.ordering = spec.ordering


class DurableExecutionApp(ts.App):

    def __init__(self, app_config: AppConfig) -> None:
        self.ordering = component.Ordering(app_config.ordering)

    def close(self) -> None:
        self.ordering.close()


class AppConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> AppConfig: ...


class EnvConfigRepository(AppConfigRepository):

    def get(self) -> AppConfig:
        ingress = os.environ.get("RESTATE_INGRESS")
        if ingress is None:
            raise errors.invalid("missing_env", "RESTATE_INGRESS is required")
        return AppConfig(Spec(ordering=component.Config(component.Spec(ingress=ingress))))


class AppLoader(ts.Loader):

    def __init__(self, app_config_repository: AppConfigRepository) -> None:
        self._app_config_repository = app_config_repository

    def load(self) -> DurableExecutionApp:
        return DurableExecutionApp(self._app_config_repository.get())


@ts.load
def load() -> DurableExecutionApp:
    return AppLoader(EnvConfigRepository()).load()
