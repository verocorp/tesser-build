from __future__ import annotations

import os
import typing

import tesser.app as ts

import alpha.component.config as alpha_config
import beta.component.config as beta_config
import tesser.errors as errors

import app.app as app
import app.config as config


class ConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> config.Config: ...


class EnvConfigRepository(ConfigRepository):

    def get(self) -> config.Config:
        storage = os.environ.get("ALPHA_STORAGE")
        if storage is None:
            raise errors.invalid("missing_env", "ALPHA_STORAGE is required")
        key = os.environ.get("BETA_KEY")
        if key is None:
            raise errors.invalid("missing_env", "BETA_KEY is required")
        return config.Config(
            config.Spec(
                alpha=alpha_config.Config(alpha_config.Spec(storage=storage)),
                beta=beta_config.Config(beta_config.Spec(key=key)),
            )
        )


class AppLoader(ts.Loader):

    def __init__(self, configs: ConfigRepository) -> None:
        self._configs = configs

    def load(self) -> app.App:
        return app.App(self._configs.get())


@ts.load
def load() -> app.App:
    return AppLoader(EnvConfigRepository()).load()
