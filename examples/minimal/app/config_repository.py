from __future__ import annotations

import os
import typing

import tesser.app as ts

import alpha.component as alpha_component
import beta.component as beta_component
import tesser.errors as errors

import app.config as config


class AppConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> config.AppConfig: ...


class EnvConfigRepository(AppConfigRepository):

    def get(self) -> config.AppConfig:
        storage = os.environ.get("ALPHA_STORAGE")
        if storage is None:
            raise errors.invalid("missing_env", "ALPHA_STORAGE is required")
        key = os.environ.get("BETA_KEY")
        if key is None:
            raise errors.invalid("missing_env", "BETA_KEY is required")
        return config.AppConfig(
            config.Spec(
                alpha=alpha_component.Config(alpha_component.Spec(storage=storage)),
                beta=beta_component.Config(beta_component.Spec(key=key)),
            )
        )
