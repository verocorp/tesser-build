from __future__ import annotations

import os

import app.repository as repository


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        os.environ.update(ALPHA_STORAGE="memory", BETA_KEY="k")
        cfg = repository.EnvConfigRepository().get()
        assert cfg.beta.key == "k"
