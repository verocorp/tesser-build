from __future__ import annotations

import typing

import tesser.app as ts

import tessercheck.component.config as tessercheck_config

import app.config as config


class ConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> config.Config: ...


class EnvConfigRepository(ConfigRepository):

    def get(self) -> config.Config:
        return config.Config(
            config.Spec(
                tessercheck=tessercheck_config.Config(tessercheck_config.Spec()),
            )
        )
