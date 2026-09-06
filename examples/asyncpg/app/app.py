from __future__ import annotations

import os
import typing

import tesser.app as ts

import alpha.adapters.gateways as gateways
import alpha.component as alpha_component
import beta.component as beta_component
import pgdatabase.database as pgdatabase
import tesser.errors as errors


class Spec(ts.Spec):

    def __init__(self, alpha: alpha_component.Config, beta: beta_component.Config) -> None:
        self.alpha = alpha
        self.beta = beta


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.alpha = spec.alpha
        self.beta = spec.beta


class AsyncpgApp(ts.App):

    def __init__(self, app_config: AppConfig) -> None:
        self.databases = pgdatabase.Databases(app_config.alpha.database, app_config.beta.database)
        beta = beta_component.Beta(
            app_config.beta, self.databases.database(app_config.beta.database)
        )
        alpha = alpha_component.Alpha(
            app_config.alpha,
            self.databases.database(app_config.alpha.database),
            gateways.BetaCheckGateway(beta.client),
        )
        self.beta = beta
        self.alpha = alpha

    async def open(self) -> None:
        await self.databases.open()

    async def close(self) -> None:
        await self.alpha.close()
        await self.beta.close()
        await self.databases.close()


class AppConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> AppConfig: ...


class EnvConfigRepository(AppConfigRepository):

    def get(self) -> AppConfig:
        alpha_storage = os.environ.get("ALPHA_STORAGE")
        if alpha_storage is None:
            raise errors.invalid("missing_env", "ALPHA_STORAGE is required")
        beta_storage = os.environ.get("BETA_STORAGE")
        if beta_storage is None:
            raise errors.invalid("missing_env", "BETA_STORAGE is required")
        return AppConfig(
            Spec(
                alpha=alpha_component.Config(alpha_component.Spec(storage=alpha_storage)),
                beta=beta_component.Config(beta_component.Spec(storage=beta_storage)),
            )
        )


class AppLoader(ts.Loader):

    def __init__(self, app_config_repository: AppConfigRepository) -> None:
        self._app_config_repository = app_config_repository

    def load(self) -> AsyncpgApp:
        return AsyncpgApp(self._app_config_repository.get())


@ts.load
def load() -> AsyncpgApp:
    return AppLoader(EnvConfigRepository()).load()
