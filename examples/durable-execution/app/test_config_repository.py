from __future__ import annotations

import os

import app.config_repository as config_repository


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        os.environ.update(RESTATE_INGRESS="http://localhost:8080")
        cfg = config_repository.EnvConfigRepository().get()
        assert cfg.ordering.ingress == "http://localhost:8080"
