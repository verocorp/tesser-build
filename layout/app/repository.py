from __future__ import annotations

from typing import Protocol

import tesser.app as ts

import repo.component.config as repo_config

import app.config as config


class ConfigRepository(ts.ConfigRepository, Protocol):

    def get(self) -> config.Config: ...


class EnvConfigRepository(ConfigRepository):

    def get(self) -> config.Config:
        return config.Config(config.Spec(repo=repo_config.Config(repo_config.Spec())))
