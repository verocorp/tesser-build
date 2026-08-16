from __future__ import annotations

import tesser.app as ts

import repo.wiring.config as repo_config

import bootstrap.config as config


class EnvConfigRepository(ts.ConfigRepository[config.Config]):

    def get(self) -> config.Config:
        return config.Config(config.Spec(repo=repo_config.Config(repo_config.Spec())))
