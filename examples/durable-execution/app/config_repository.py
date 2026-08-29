from __future__ import annotations

import os
import typing

import tesser.app as ts

import ordering.component.config as ordering_config
import tesser.errors as errors

import app.config as config


class ConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> config.Config: ...


class EnvConfigRepository(ConfigRepository):

    def get(self) -> config.Config:
        ingress = os.environ.get("RESTATE_INGRESS")
        if ingress is None:
            raise errors.invalid("missing_env", "RESTATE_INGRESS is required")
        return config.Config(
            config.Spec(ordering=ordering_config.Config(ordering_config.Spec(ingress=ingress)))
        )
