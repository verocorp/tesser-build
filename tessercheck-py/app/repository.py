from __future__ import annotations

import typing

import tesser.app as ts

import tessercheck.component as component

import app.config as config


class ConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> config.AppConfig: ...


class EnvConfigRepository(ConfigRepository):

    def get(self) -> config.AppConfig:
        return config.AppConfig(
            config.Spec(
                tessercheck=component.Config(component.Spec()),
            )
        )
