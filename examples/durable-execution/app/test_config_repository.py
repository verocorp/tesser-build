from __future__ import annotations

import app.config as config
import app.config_repository as config_repository


class TestEnvConfigRepository:

    def test_the_environment_the_runner_supplied_is_read_into_a_config(self) -> None:
        cfg = config_repository.EnvConfigRepository().get()
        assert isinstance(cfg, config.Config)
        assert cfg.ordering.ingress == "http://localhost:8080"

    def test_each_read_returns_its_own_config(self) -> None:
        reader = config_repository.EnvConfigRepository()
        assert reader.get() is not reader.get()
