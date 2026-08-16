from __future__ import annotations

import tesser.app as ts

import tessercheck.wiring.config as tessercheck_config

import bootstrap.config as config


class EnvConfigRepository(ts.ConfigRepository[config.Config]):

    def get(self) -> config.Config:
        return config.Config(
            config.Spec(
                tessercheck=tessercheck_config.Config(tessercheck_config.Spec()),
            )
        )
