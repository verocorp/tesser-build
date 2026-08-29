from __future__ import annotations

import os

import app.config_repository as config_repository


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        cfg = config_repository.EnvConfigRepository().get()
        assert cfg.alpha.storage == os.environ["ALPHA_STORAGE"]
        assert cfg.beta.storage == os.environ["BETA_STORAGE"]
