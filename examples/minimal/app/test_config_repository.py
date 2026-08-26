from __future__ import annotations

import os

import app.config_repository as config_repository


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        os.environ.update(ALPHA_STORAGE="memory", BETA_KEY="k")
        cfg = config_repository.EnvConfigRepository().get()
        assert cfg.beta.key == "k"
